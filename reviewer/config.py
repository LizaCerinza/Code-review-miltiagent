"""Configuración del revisor: valores por defecto, variables de entorno y argumentos de la CLI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from typing import Any

PROVIDER_VALUES = ("azure", "anthropic")
# Modelo por defecto según el proveedor. En Azure es el nombre del deployment.
DEFAULT_MODELS = {"azure": "gpt-4.1-mini", "anthropic": "claude-opus-5-5"}
DEFAULT_AZURE_API_VERSION = "2024-10-21"
AGENT_NAMES = ("functional", "security", "design")
FAIL_ON_VALUES = ("critical", "major", "minor", "info", "none")
EFFORT_VALUES = ("low", "medium", "high", "xhigh", "max")


class ConfigError(ValueError):
    """Configuración inválida: el CLI la convierte en código de salida 2."""


@dataclass(frozen=True)
class ReviewConfig:
    provider: str = "azure"
    # Vacío = el modelo por defecto del proveedor (DEFAULT_MODELS).
    model: str = ""
    # Modelo por agente; si un agente no aparece aquí usa `model`.
    agent_models: Mapping[str, str] = field(default_factory=dict)
    effort: str = "high"  # solo Anthropic
    azure_api_version: str = DEFAULT_AZURE_API_VERSION
    max_tokens: int = 32_000
    agent_timeout: float = 600.0
    fail_on: str = "critical"
    fail_on_agent_error: bool = False
    tasks_dir: str = "docs/tasks"
    spec_globs: tuple[str, ...] = ("openspec/specs/**/*.md",)
    guidelines_file: str = "REVIEW_GUIDELINES.md"
    skills_dir: str = ".review-skills"
    max_file_chars: int = 60_000
    max_context_chars: int = 300_000
    output_dir: str = "."
    sonar_host: str = "https://sonarcloud.io"

    def model_for(self, agent: str) -> str:
        return self.agent_models.get(agent) or self.model or DEFAULT_MODELS[self.provider]

    def with_overrides(self, **overrides: Any) -> ReviewConfig:
        """Aplica los valores que no son None (por ejemplo, argumentos de la CLI)."""
        known = {f.name for f in fields(self)}
        changes = {k: v for k, v in overrides.items() if v is not None and k in known}
        return replace(self, **changes).validated()

    def validated(self) -> ReviewConfig:
        if self.provider not in PROVIDER_VALUES:
            raise ConfigError(
                f"provider debe ser uno de {', '.join(PROVIDER_VALUES)}; "
                f"se recibió '{self.provider}'"
            )
        if self.fail_on not in FAIL_ON_VALUES:
            raise ConfigError(
                f"fail-on debe ser uno de {', '.join(FAIL_ON_VALUES)}; se recibió '{self.fail_on}'"
            )
        if self.effort not in EFFORT_VALUES:
            raise ConfigError(
                f"effort debe ser uno de {', '.join(EFFORT_VALUES)}; se recibió '{self.effort}'"
            )
        if self.agent_timeout <= 0:
            raise ConfigError("el tiempo máximo por agente debe ser mayor que 0")
        return self

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ReviewConfig:
        """Lee la configuración de variables de entorno `REVIEWER_*` (vacías = por defecto)."""

        def get(name: str) -> str | None:
            value = env.get(name, "").strip()
            return value or None

        agent_models = {
            agent: model
            for agent in AGENT_NAMES
            if (model := get(f"REVIEWER_MODEL_{agent.upper()}"))
        }
        spec_globs = get("REVIEWER_SPEC_GLOBS")
        timeout = get("REVIEWER_AGENT_TIMEOUT")
        fail_on_error = get("REVIEWER_FAIL_ON_AGENT_ERROR")
        try:
            return cls().with_overrides(
                provider=get("REVIEWER_PROVIDER"),
                model=get("REVIEWER_MODEL"),
                agent_models=agent_models or None,
                effort=get("REVIEWER_EFFORT"),
                agent_timeout=float(timeout) if timeout else None,
                fail_on=get("REVIEWER_FAIL_ON"),
                fail_on_agent_error=_parse_bool(fail_on_error) if fail_on_error else None,
                tasks_dir=get("REVIEWER_TASKS_DIR"),
                spec_globs=_split_globs(spec_globs) if spec_globs else None,
                guidelines_file=get("REVIEWER_GUIDELINES_FILE"),
                skills_dir=get("REVIEWER_SKILLS_DIR"),
                output_dir=get("REVIEWER_OUTPUT_DIR"),
                sonar_host=get("SONAR_HOST_URL"),
                azure_api_version=get("AZURE_OPENAI_API_VERSION"),
            )
        except ValueError as error:
            raise ConfigError(str(error)) from error


def _parse_bool(value: str) -> bool:
    lowered = value.lower()
    if lowered in ("1", "true", "yes", "si", "sí"):
        return True
    if lowered in ("0", "false", "no"):
        return False
    raise ConfigError(f"valor booleano inválido: '{value}'")


def _split_globs(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.replace("\n", ",").split(",") if part.strip())
