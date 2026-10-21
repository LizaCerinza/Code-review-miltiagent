"""CLI: `python -m reviewer` revisa un PR de GitHub o la rama local contra una base."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import httpx

from . import __version__
from .config import FAIL_ON_VALUES, PROVIDER_VALUES, ConfigError, ReviewConfig
from .context import (
    SONAR_NOT_CONFIGURED,
    SONAR_OK,
    SONAR_UNAVAILABLE,
    ReviewContext,
    build_context,
    local_git_diff,
)
from .github import DEFAULT_API_URL, GitHubClient
from .llm import create_provider, missing_credentials
from .models import ReviewResult
from .orchestrator import graph_mermaid, review
from .publisher import publish
from .report import render_summary
from .skills.repo import skills_from_git, skills_from_github
from .sonar import fetch_pr_issues, read_project_key

log = logging.getLogger("reviewer")

EXIT_OK, EXIT_BLOCKING, EXIT_ERROR = 0, 1, 2
REPORT_FILE = "ai-review.json"


class UsageError(Exception):
    """Error que impide revisar (configuración, credenciales, PR inexistente)."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m reviewer",
        description="Code review multiagente (funcional, seguridad y diseño) para pull requests.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--print-graph", action="store_true",
                        help="imprime el grafo de agentes (Mermaid) y termina")
    target = parser.add_argument_group("qué revisar")
    target.add_argument("--repo", help="owner/repo (por defecto, GITHUB_REPOSITORY)")
    target.add_argument("--pr", type=int, help="número del PR (por defecto, REVIEWER_PR_NUMBER)")
    target.add_argument("--local", action="store_true",
                        help="revisa la rama local contra --base, sin publicar en GitHub")
    target.add_argument("--base", default="main",
                        help="rama base en modo local (por defecto: main)")
    target.add_argument("--workspace", default=".", help="checkout del repo revisado")
    target.add_argument("--dry-run", action="store_true",
                        help="en modo PR, revisa pero no publica nada en GitHub")

    opts = parser.add_argument_group("opciones (también por variables REVIEWER_*)")
    opts.add_argument("--provider", choices=PROVIDER_VALUES,
                      help="proveedor de modelos (por defecto: azure)")
    opts.add_argument("--fail-on", choices=FAIL_ON_VALUES)
    opts.add_argument("--fail-on-agent-error", action="store_true", default=None)
    opts.add_argument("--model", help="modelo o, en Azure, nombre del deployment")
    opts.add_argument("--effort")
    opts.add_argument("--agent-timeout", type=float)
    opts.add_argument("--tasks-dir")
    opts.add_argument("--spec-glob", action="append", dest="spec_globs")
    opts.add_argument("--guidelines-file")
    opts.add_argument("--skills-dir",
                      help="carpeta de skills del repo (por defecto: .review-skills)")
    opts.add_argument("--output-dir")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.print_graph:
        print(graph_mermaid())
        return EXIT_OK
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        config = ReviewConfig.from_env(env).with_overrides(
            provider=args.provider,
            fail_on=args.fail_on,
            fail_on_agent_error=args.fail_on_agent_error,
            model=args.model,
            effort=args.effort,
            agent_timeout=args.agent_timeout,
            tasks_dir=args.tasks_dir,
            spec_globs=tuple(args.spec_globs) if args.spec_globs else None,
            guidelines_file=args.guidelines_file,
            skills_dir=args.skills_dir,
            output_dir=args.output_dir,
        )
        return run(args, config, env)
    except (ConfigError, UsageError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_ERROR


def run(args: argparse.Namespace, config: ReviewConfig, env: Mapping[str, str]) -> int:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise UsageError(f"el workspace '{workspace}' no existe")

    gh: GitHubClient | None = None
    pr = 0
    head_sha = ""
    if args.local:
        _require_model_credentials(config, env)
        ctx = _local_context(workspace, config, args.base)
    else:
        repo = args.repo or env.get("GITHUB_REPOSITORY", "")
        pr = args.pr or int(env.get("REVIEWER_PR_NUMBER", "0") or 0)
        token = env.get("GITHUB_TOKEN", "")
        if not repo or not pr:
            raise UsageError("indica --repo y --pr, o usa --local para revisar la rama local")
        if not token:
            raise UsageError("falta GITHUB_TOKEN para leer el PR")
        _require_model_credentials(config, env)
        gh = GitHubClient(token, repo, api_url=env.get("GITHUB_API_URL") or DEFAULT_API_URL)
        ctx, head_sha = _pr_context(gh, pr, workspace, config, env)

    result = asyncio.run(review(ctx, config, provider=create_provider(config, env)))
    summary = render_summary(result)
    _write_outputs(result, summary, config, env)
    print(summary)

    if gh is not None and not args.dry_run:
        try:
            posted = publish(gh, pr, head_sha, result, ctx.files)
            log.info("Revisión publicada en el PR #%s (%s comentarios inline nuevos).", pr, posted)
        except httpx.HTTPError as error:
            log.error("No se pudo publicar la revisión en GitHub: %s", error)
            return EXIT_ERROR
        finally:
            gh.close()
    return EXIT_BLOCKING if result.failed else EXIT_OK


def _require_model_credentials(config: ReviewConfig, env: Mapping[str, str]) -> None:
    missing = missing_credentials(config.provider, env)
    if missing:
        raise UsageError(
            f"faltan las credenciales del proveedor '{config.provider}': {', '.join(missing)}"
        )


def _local_context(workspace: Path, config: ReviewConfig, base: str) -> ReviewContext:
    try:
        files = local_git_diff(workspace, base)
        # Los mensajes de commit hacen de "descripción": ahí puede ir el hashtag de la tarea.
        messages = subprocess.run(
            ["git", "-C", str(workspace), "log", "--format=%B", f"{base}..HEAD"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        raise UsageError(f"no se pudo obtener el diff contra '{base}': {error}") from error
    skill_files, skill_notes = skills_from_git(workspace, base, config.skills_dir)
    return build_context(workspace, config, f"Cambios locales {base}...HEAD", messages, files,
                         repo_skill_files=skill_files, skill_notes=skill_notes)


def _pr_context(
    gh: GitHubClient, pr: int, workspace: Path, config: ReviewConfig, env: Mapping[str, str]
) -> tuple[ReviewContext, str]:
    try:
        pull = gh.get_pull(pr)
        files = gh.list_files(pr)
    except httpx.HTTPStatusError as error:
        raise UsageError(
            f"no se pudo leer el PR #{pr} de {gh.repo}: HTTP {error.response.status_code}"
        ) from error

    sonar_issues: list[dict] = []
    sonar_status = SONAR_NOT_CONFIGURED
    sonar_token = env.get("SONAR_TOKEN", "")
    project_key = env.get("SONAR_PROJECT_KEY") or read_project_key(workspace)
    if sonar_token and project_key:
        issues = fetch_pr_issues(config.sonar_host, sonar_token, project_key, pr)
        sonar_status = SONAR_UNAVAILABLE if issues is None else SONAR_OK
        sonar_issues = issues or []

    # Skills del repo desde la rama base: el PR no puede debilitar su propia revisión.
    skill_files, skill_notes = skills_from_github(gh, pull["base"]["sha"], config.skills_dir)
    ctx = build_context(workspace, config, pull.get("title") or "", pull.get("body") or "",
                        files, sonar_issues, sonar_status,
                        repo_skill_files=skill_files, skill_notes=skill_notes)
    return ctx, pull["head"]["sha"]


def _write_outputs(
    result: ReviewResult, summary: str, config: ReviewConfig, env: Mapping[str, str]
) -> None:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {"failed": result.failed, **result.model_dump(mode="json")}
    (output_dir / REPORT_FILE).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    step_summary = env.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(summary + "\n")


if __name__ == "__main__":
    sys.exit(main())
