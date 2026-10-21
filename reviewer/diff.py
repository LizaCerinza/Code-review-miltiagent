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


_NUMBER_WIDTH = 5
_LINE_NUMBER_PREFIX_RE = re.compile(r"^ *(\d+)? \| ")


def number_patch(patch: str) -> str:
    """Anota cada línea del diff con su número en la versión nueva del archivo.

    Los modelos chicos calculan mal las líneas a partir de los encabezados `@@`; con el
    número a la vista, solo tienen que copiarlo. Las líneas eliminadas no tienen número.

        @@ -1,2 +1,3 @@
            1 |  linea de contexto
            2 | +linea agregada
              | -linea eliminada
    """
    out: list[str] = []
    new_line: int | None = None
    blank = " " * _NUMBER_WIDTH
    for raw in patch.splitlines():
        match = _HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            out.append(raw)
            continue
        if new_line is None or raw.startswith("\\"):
            out.append(raw)
            continue
        if raw.startswith("-"):
            out.append(f"{blank} | {raw}")
            continue
        out.append(f"{new_line:>{_NUMBER_WIDTH}} | {raw}")
        new_line += 1
    return "\n".join(out)


def number_lines(text: str) -> str:
    """Contenido completo de un archivo con números de línea."""
    return "\n".join(
        f"{n:>{_NUMBER_WIDTH}} | {line}" for n, line in enumerate(text.splitlines(), start=1)
    )


def strip_line_numbers(text: str) -> str:
    """Quita los prefijos `  52 | ` que un modelo copie dentro de la evidencia."""
    lines = [line for line in text.splitlines() if line.strip()]
    matches = [_LINE_NUMBER_PREFIX_RE.match(line) for line in lines]
    if not lines or not all(matches) or not any(m.group(1) for m in matches if m):
        return text
    return "\n".join(_LINE_NUMBER_PREFIX_RE.sub("", line, count=1) for line in text.splitlines())


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
