"""Skills de revisión: conocimiento de cada agente en archivos SKILL.md.

Formato:

    ---
    name: ci-workflows               # kebab-case, único
    agent: security                  # functional | security | design | all
    description: Seguridad en workflows de GitHub Actions
    applies_to: [".github/**"]       # opcional; sin él, la skill aplica siempre
    ---
    Instrucciones de revisión en Markdown.

El orquestador (no el modelo) decide qué skills recibe cada agente, según los archivos
que cambia el PR.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

AGENTS = ("functional", "security", "design", "all")
LIBRARY = Path(__file__).parent / "library"
MAX_SKILL_CHARS = 20_000

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---[ \t]*\n?(.*)\Z", re.DOTALL)


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    agent: str
    description: str
    body: str
    applies_to: tuple[str, ...] = ()
    source: str = ""

    def applies(self, agent: str, paths: Iterable[str]) -> bool:
        if self.agent not in (agent, "all"):
            return False
        if not self.applies_to:
            return True
        return any(_matches(path, pattern) for path in paths for pattern in self.applies_to)


def _matches(path: str, pattern: str) -> bool:
    # fnmatch: `*` también cruza `/`, así que `src/**/*.ts` cubre cualquier profundidad.
    # `**/x` también debe coincidir con `x` en la raíz.
    return fnmatch.fnmatch(path, pattern) or (
        pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:])
    )


def parse_skill(text: str, source: str = "") -> Skill:
    text = text.replace("\r\n", "\n").lstrip("﻿")
    if len(text) > MAX_SKILL_CHARS:
        raise SkillError(f"supera el máximo de {MAX_SKILL_CHARS} caracteres")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillError("falta el encabezado YAML entre líneas '---'")
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise SkillError(f"encabezado YAML inválido: {error}") from error
    if not isinstance(meta, dict):
        raise SkillError("el encabezado YAML debe ser un objeto")

    name = meta.get("name")
    agent = meta.get("agent")
    description = meta.get("description")
    applies_to = meta.get("applies_to", [])
    body = match.group(2).strip()

    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise SkillError("`name` es obligatorio y debe estar en kebab-case")
    if agent not in AGENTS:
        raise SkillError(f"`agent` debe ser uno de {', '.join(AGENTS)}")
    if not isinstance(description, str) or not description.strip():
        raise SkillError("`description` es obligatoria")
    if isinstance(applies_to, str):
        applies_to = [applies_to]
    if not isinstance(applies_to, list) or not all(isinstance(p, str) for p in applies_to):
        raise SkillError("`applies_to` debe ser una lista de patrones")
    if not body:
        raise SkillError("el cuerpo de la skill está vacío")
    return Skill(name=name, agent=agent, description=description.strip(), body=body,
                 applies_to=tuple(applies_to), source=source)


def load_builtin_skills() -> list[Skill]:
    """Skills incluidas en el revisor. Un error aquí es un bug del revisor: se propaga."""
    return [
        parse_skill(
            path.read_text(encoding="utf-8"), f"builtin:{path.relative_to(LIBRARY).as_posix()}"
        )
        for path in sorted(LIBRARY.rglob("SKILL.md"))
    ]


def parse_repo_skills(files: Mapping[str, str]) -> tuple[list[Skill], list[str]]:
    """Parsea las skills del repo objetivo. Las inválidas se ignoran y se informan."""
    skills: list[Skill] = []
    notes: list[str] = []
    for path, text in sorted(files.items()):
        try:
            skills.append(parse_skill(text, f"repo:{path}"))
        except SkillError as error:
            notes.append(f"Skill ignorada `{path}`: {error}.")
    return skills, notes


def merge_skills(builtin: list[Skill], repo: list[Skill]) -> list[Skill]:
    """Una skill del repo con el mismo `name` reemplaza a la incluida."""
    merged = {skill.name: skill for skill in builtin}
    for skill in repo:
        merged[skill.name] = skill
    return list(merged.values())


def select_skills(skills: list[Skill], agent: str, paths: Iterable[str]) -> list[Skill]:
    paths = list(paths)
    return [skill for skill in skills if skill.applies(agent, paths)]
