"""Lectura de las skills del repo objetivo desde la rama BASE del PR.

Nunca se leen del checkout del PR: si no, el propio PR podría editar una skill para
debilitar la revisión que se le aplica.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import httpx

from ..github import GitHubClient

log = logging.getLogger(__name__)

SKILL_FILE = "SKILL.md"


def _is_skill(path: str, skills_dir: str) -> bool:
    prefix = skills_dir.strip("/") + "/"
    return path.startswith(prefix) and path.rsplit("/", 1)[-1] == SKILL_FILE


def skills_from_github(
    gh: GitHubClient, base_sha: str, skills_dir: str
) -> tuple[dict[str, str], list[str]]:
    """Skills del repo en el commit base, vía la API de GitHub. Devuelve (archivos, notas)."""
    try:
        paths = [p for p in gh.list_tree_paths(base_sha) if _is_skill(p, skills_dir)]
        return {path: gh.get_file_text(path, base_sha) for path in paths}, []
    except (httpx.HTTPError, KeyError, ValueError) as error:
        log.warning("No se pudieron leer las skills del repo: %s", error)
        return {}, [f"No se pudieron leer las skills del repo (`{skills_dir}`): se usaron solo "
                    "las skills incluidas en el revisor."]


def skills_from_git(
    workspace: Path, base: str, skills_dir: str
) -> tuple[dict[str, str], list[str]]:
    """Skills del repo en la rama `base`, leídas con git (modo local)."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(workspace), *args],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout

    try:
        listing = git("ls-tree", "-r", "--name-only", base, "--", skills_dir.strip("/"))
        paths = [p for p in listing.splitlines() if _is_skill(p, skills_dir)]
        return {path: git("show", f"{base}:{path}") for path in paths}, []
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        log.warning("No se pudieron leer las skills del repo con git: %s", error)
        return {}, [f"No se pudieron leer las skills del repo (`{skills_dir}`) desde `{base}`: "
                    "se usaron solo las skills incluidas en el revisor."]
