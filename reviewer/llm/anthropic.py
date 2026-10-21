"""Proveedor Anthropic (Claude) con salida estructurada nativa."""

from __future__ import annotations

from typing import Any

import anthropic

from ..config import ReviewConfig
from ..models import Usage
from .base import LLMError, LLMProvider, LLMResponse

# Beta que activa `fallbacks: "default"`: si el modelo declina por política, la API
# reintenta la misma petición con el modelo de respaldo recomendado, en el servidor.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, client: anthropic.AsyncAnthropic | None = None):
        self._client = client or anthropic.AsyncAnthropic()

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        config: ReviewConfig,
    ) -> LLMResponse:
        # Streaming: el contexto puede ser largo y evita timeouts HTTP con max_tokens alto.
        async with self._client.beta.messages.stream(
            model=model,
            max_tokens=config.max_tokens,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": config.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
        ) as stream:
            response = await stream.get_final_message()

        if response.stop_reason == "refusal":
            raise LLMError("el modelo declinó la revisión")
        if response.stop_reason == "max_tokens":
            raise LLMError("la respuesta se cortó por max_tokens")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise LLMError("la respuesta no tiene texto")
        usage = getattr(response, "usage", None)
        return LLMResponse(
            text=text,
            model=getattr(response, "model", "") or model,
            usage=Usage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
            ),
        )
