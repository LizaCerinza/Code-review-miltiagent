"""Utilidades para diffs unificados (formato de git y de la API de GitHub)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class ChangedFile:
    path: str
    status: str  # added | modified | removed | renamed
    patch: str = ""


def commentable_lines(patch: str) -> set[int]:
    """Líneas de la versión nueva que GitHub acepta para un comentario inline (lado RIGHT).

    Son las líneas agregadas y las de contexto que aparecen dentro de algún hunk.
    """
    lines: set[int] = set()
    new_line: int | None = None
    for raw in patch.splitlines():
        match = _HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            continue
        if new_line is None or raw.startswith("\\"):
            continue
        if raw.startswith("-"):
            continue
        lines.add(new_line)
        new_line += 1
    return lines


def split_unified_diff(diff: str) -> list[ChangedFile]:
    """Divide la salida de `git diff` en un ChangedFile por archivo."""
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    patch_lines: list[str] = []
    old_path = ""

    def flush() -> None:
        if current is not None:
            current.patch = "\n".join(patch_lines)
            files.append(current)

    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            flush()
            # Ruta de respaldo para cambios sin líneas ---/+++ (rename puro, binarios).
            header_path = raw.rsplit(" b/", 1)[-1] if " b/" in raw else ""
            current = ChangedFile(path=header_path, status="modified")
            patch_lines, old_path = [], ""
            continue
        if current is None:
            continue
        if not patch_lines:
            if raw.startswith("new file mode"):
                current.status = "added"
            elif raw.startswith("deleted file mode"):
                current.status = "removed"
            elif raw.startswith("rename from "):
                current.status = "renamed"
            elif raw.startswith("rename to "):
                current.path = raw[len("rename to "):].strip()
            elif raw.startswith("--- "):
                old_path = _strip_prefix(raw[4:])
            elif raw.startswith("+++ "):
                new_path = _strip_prefix(raw[4:])
                current.path = old_path if new_path == "/dev/null" else new_path
            elif raw.startswith("@@"):
                patch_lines.append(raw)
            continue
        patch_lines.append(raw)
    flush()
    return [f for f in files if f.path]


def _strip_prefix(path: str) -> str:
    path = path.strip()
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path
