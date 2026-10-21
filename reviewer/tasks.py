"""Resolución de la tarea del PR a partir de hashtags (`#<nombre>` → `<tasks_dir>/<nombre>.md`)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# `#` no precedido por letra, dígito, `&` o `/` (excluye anclas de URL y entidades HTML),
# seguido de un nombre que empieza con letra o dígito. Los títulos Markdown (`# Título`)
# no coinciden porque después del `#` va un espacio.
_HASHTAG_RE = re.compile(r"(?<![\w&/#])#([A-Za-z0-9][A-Za-z0-9._-]*)")
_NUMERIC_RE = re.compile(r"\d+")


@dataclass
class TaskResolution:
    found: dict[str, str] = field(default_factory=dict)  # ruta relativa -> contenido
    missing: list[tuple[str, str]] = field(default_factory=list)  # (hashtag, ruta buscada)

    @property
    def referenced(self) -> bool:
        return bool(self.found or self.missing)


def extract_task_names(*texts: str) -> list[str]:
    """Nombres de tarea referenciados, sin duplicados y en orden de aparición."""
    names: list[str] = []
    for text in texts:
        for match in _HASHTAG_RE.finditer(text or ""):
            name = match.group(1).rstrip("._-")
            if name.lower().endswith(".md"):
                name = name[:-3]
            if not name or _NUMERIC_RE.fullmatch(name) or ".." in name:
                continue
            if name not in names:
                names.append(name)
    return names


def resolve_tasks(workspace: Path, tasks_dir: str, title: str, description: str) -> TaskResolution:
    root = (workspace / tasks_dir).resolve()
    resolution = TaskResolution()
    for name in extract_task_names(title, description):
        relative = f"{tasks_dir.rstrip('/')}/{name}.md"
        path = (root / f"{name}.md").resolve()
        # Defensa adicional: la ruta final debe quedar dentro de la carpeta de tareas.
        if not path.is_relative_to(root) or not path.is_file():
            resolution.missing.append((name, relative))
            continue
        resolution.found[relative] = path.read_text(encoding="utf-8")
    return resolution
