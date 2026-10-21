"""Contexto del PR para los agentes: diff, archivos, tareas, especificaciones, guías y Sonar."""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .config import ReviewConfig
from .diff import ChangedFile, split_unified_diff
from .skills import Skill, load_builtin_skills, merge_skills, parse_repo_skills
from .tasks import TaskResolution, resolve_tasks

log = logging.getLogger(__name__)

# Archivos que no aportan a la revisión y que pueden ser enormes.
IGNORED_PATTERNS = (
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "*.lock",
    "dist/*",
    "build/*",
    "coverage/*",
    "*.min.js",
    "*.map",
    "*.snap",
)
# Carpetas que no se listan en el índice del repo.
_INDEX_SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".venv", "venv",
                    "__pycache__", ".pytest_cache", ".ruff_cache", ".next", ".turbo"}
MAX_INDEX_PATHS = 3_000

# Etiquetas que delimitan los datos del PR en los prompts.
DATA_TAGS = ("pull_request", "diff", "archivos", "archivo", "tareas", "tarea",
             "especificaciones", "guias", "sonar", "indice_repo")
_CLOSING_TAG_RE = re.compile(r"</(" + "|".join(DATA_TAGS) + r")\b", re.IGNORECASE)

SONAR_OK = "ok"
SONAR_UNAVAILABLE = "unavailable"
SONAR_NOT_CONFIGURED = "not_configured"


def block(tag: str, text: str, attrs: str = "") -> str:
    """Envuelve datos no confiables en una etiqueta.

    Neutraliza las etiquetas de cierre que aparezcan dentro del contenido, para que un
    PR no pueda "cerrar" el bloque de datos e inyectar texto fuera de él.
    """
    safe = _CLOSING_TAG_RE.sub(r"<\\/\1", text)
    opening = f"<{tag} {attrs}>" if attrs else f"<{tag}>"
    return f"{opening}\n{safe}\n</{tag}>"


@dataclass
class ReviewContext:
    title: str
    description: str
    files: list[ChangedFile]
    file_contents: dict[str, str] = field(default_factory=dict)
    omitted: list[str] = field(default_factory=list)
    tasks: TaskResolution = field(default_factory=TaskResolution)
    specs: dict[str, str] = field(default_factory=dict)
    guidelines: str = ""
    guidelines_file: str = "REVIEW_GUIDELINES.md"
    sonar_issues: list[dict] = field(default_factory=list)
    sonar_status: str = SONAR_NOT_CONFIGURED
    repo_index: list[str] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    skill_notes: list[str] = field(default_factory=list)

    @property
    def has_guidelines(self) -> bool:
        """True si las guías tienen contenido además de títulos."""
        return any(
            line.strip() and not line.lstrip().startswith("#")
            for line in self.guidelines.splitlines()
        )

    def render_pull_request(self) -> str:
        """Bloque común a los 3 agentes: metadatos del PR, diff y contenido de los archivos."""
        meta = f"Título: {self.title}\nDescripción:\n{self.description or '(sin descripción)'}"
        parts = [block("pull_request", meta)]

        diff_parts = []
        for f in self.files:
            diff_parts.append(f"### {f.path} ({f.status})")
            diff_parts.append(f"```diff\n{f.patch}\n```" if f.patch else "(sin diff textual)")
        parts.append(block("diff", "\n".join(diff_parts) or "(el PR no tiene cambios revisables)"))

        if self.file_contents:
            contents = "\n".join(
                block("archivo", content, f'path="{path}"')
                for path, content in self.file_contents.items()
            )
            parts.append(block("archivos", contents))

        if self.omitted:
            parts.append(
                "Nota del revisor: por tamaño no se incluyó el contenido completo de: "
                + ", ".join(self.omitted)
                + ". Revisa esos archivos solo a partir del diff."
            )
        return "\n\n".join(parts)

    def render_tasks(self) -> str:
        if not self.tasks.found:
            return block("tareas", "(el PR no referencia ninguna tarea existente; valida solo "
                                   "contra las especificaciones)")
        body = "\n".join(
            block("tarea", content, f'path="{path}"') for path, content in self.tasks.found.items()
        )
        return block("tareas", body)

    def render_specs(self) -> str:
        if not self.specs:
            return block("especificaciones", "(no se encontraron especificaciones)")
        body = "\n\n".join(f"## {path}\n{content}" for path, content in self.specs.items())
        return block("especificaciones", body)

    def render_guidelines(self) -> str:
        if not self.has_guidelines:
            return block("guias", f"(sin guías definidas: {self.guidelines_file} no existe o está "
                                  "vacío; usa como referencia las convenciones del código)")
        return block("guias", self.guidelines.strip())

    def render_sonar(self) -> str:
        if self.sonar_status == SONAR_UNAVAILABLE:
            text = ("(issues de Sonar no disponibles: no se pudieron descartar duplicados; "
                    "reporta todo lo que encuentres)")
        elif self.sonar_status == SONAR_NOT_CONFIGURED:
            text = "(Sonar no está configurado para esta revisión)"
        elif not self.sonar_issues:
            text = "(Sonar no reportó issues abiertos en este PR)"
        else:
            text = json.dumps(self.sonar_issues, ensure_ascii=False, indent=2)
        return block("sonar", text)

    def render_repo_index(self) -> str:
        return block("indice_repo", "\n".join(self.repo_index) or "(no disponible)")


def is_ignored(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in IGNORED_PATTERNS)


def filter_files(files: list[ChangedFile]) -> list[ChangedFile]:
    return [f for f in files if not is_ignored(f.path)]


def load_specs(workspace: Path, globs: tuple[str, ...]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for pattern in globs:
        for path in sorted(workspace.glob(pattern)):
            if path.is_file():
                specs[path.relative_to(workspace).as_posix()] = path.read_text(encoding="utf-8")
    return specs


def load_guidelines(workspace: Path, name: str) -> str:
    path = workspace / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load_file_contents(
    workspace: Path, files: list[ChangedFile], max_file_chars: int, max_total_chars: int
) -> tuple[dict[str, str], list[str]]:
    """Lee del workspace los archivos cambiados, respetando un presupuesto de tamaño.

    Lo que no entra se informa explícitamente: nunca se trunca un archivo a la mitad.
    """
    contents: dict[str, str] = {}
    omitted: list[str] = []
    budget = max_total_chars
    for f in files:
        if f.status == "removed":
            continue
        path = workspace / f.path
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binario
        if len(text) > max_file_chars or len(text) > budget:
            omitted.append(f.path)
            continue
        contents[f.path] = text
        budget -= len(text)
    if omitted:
        log.warning("Contenido omitido por tamaño: %s", ", ".join(omitted))
    return contents, omitted


def build_repo_index(workspace: Path) -> list[str]:
    """Rutas de archivos del repo (sin dependencias ni artefactos), para el agente de diseño."""
    paths: list[str] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = sorted(d for d in dirs if d not in _INDEX_SKIP_DIRS)
        for name in sorted(files):
            rel = (Path(root) / name).relative_to(workspace).as_posix()
            if not is_ignored(rel):
                paths.append(rel)
            if len(paths) >= MAX_INDEX_PATHS:
                return paths
    return paths


def local_git_diff(workspace: Path, base: str) -> list[ChangedFile]:
    """Diff de la rama actual contra `base` (modo local, sin PR)."""
    output = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--no-color", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    return split_unified_diff(output)


def build_context(
    workspace: Path,
    config: ReviewConfig,
    title: str,
    description: str,
    files: list[ChangedFile],
    sonar_issues: list[dict] | None = None,
    sonar_status: str = SONAR_NOT_CONFIGURED,
    repo_skill_files: Mapping[str, str] | None = None,
    skill_notes: list[str] | None = None,
) -> ReviewContext:
    """Arma el contexto. `repo_skill_files` debe venir de la rama base, no del PR."""
    files = filter_files(files)
    contents, omitted = load_file_contents(
        workspace, files, config.max_file_chars, config.max_context_chars
    )
    repo_skills, notes = parse_repo_skills(repo_skill_files or {})
    notes = list(skill_notes or []) + notes
    skills_prefix = config.skills_dir.strip("/") + "/"
    if any(f.path.startswith(skills_prefix) for f in files):
        notes.append(f"Este PR modifica skills de revisión (`{config.skills_dir}`): se usó la "
                     "versión de la rama base; los cambios se aplicarán después del merge.")
    return ReviewContext(
        title=title,
        description=description,
        files=files,
        file_contents=contents,
        omitted=omitted,
        tasks=resolve_tasks(workspace, config.tasks_dir, title, description),
        specs=load_specs(workspace, config.spec_globs),
        guidelines=load_guidelines(workspace, config.guidelines_file),
        guidelines_file=config.guidelines_file,
        sonar_issues=sonar_issues or [],
        sonar_status=sonar_status,
        repo_index=build_repo_index(workspace),
        skills=merge_skills(load_builtin_skills(), repo_skills),
        skill_notes=notes,
    )
