"""Proveedores de modelos: Azure OpenAI (por defecto) y Anthropic."""

from __future__ import annotations

from collections.abc import Mapping

from ..config import ReviewConfig
from .base import LLMError, LLMProvider, LLMResponse

# Variables de entorno que necesita cada proveedor.
REQUIRED_CREDENTIALS = {
    "azure": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    "anthropic": ("ANTHROPIC_API_KEY",),
}
# Anthropic también acepta un token OAuth o un perfil de `ant auth login`.
_ANTHROPIC_ALTERNATIVES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE")


def missing_credentials(provider: str, env: Mapping[str, str]) -> list[str]:
    """Variables de credenciales que faltan para el proveedor elegido."""
    if provider == "anthropic":
        if any(env.get(name, "").strip() for name in _ANTHROPIC_ALTERNATIVES):
            return []
        return list(REQUIRED_CREDENTIALS["anthropic"])
    return [name for name in REQUIRED_CREDENTIALS[provider] if not env.get(name, "").strip()]


def create_provider(config: ReviewConfig, env: Mapping[str, str]) -> LLMProvider:
    if config.provider == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    from .azure import AzureOpenAIProvider

    return AzureOpenAIProvider(
        endpoint=env.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=env.get("AZURE_OPENAI_API_KEY", ""),
        api_version=config.azure_api_version,
    )


__all__ = ["LLMError", "LLMProvider", "LLMResponse", "create_provider", "missing_credentials"]
