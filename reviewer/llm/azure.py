"""Proveedor Azure OpenAI (por defecto, el deployment `gpt-4.1-mini`) con salida estructurada."""

from __future__ import annotations

from typing import Any

import openai

from ..config import ReviewConfig
from ..models import Usage
from .base import LLMError, LLMProvider, LLMResponse

# Temperatura baja: la revisión debe ser lo más estable posible entre ejecuciones.
TEMPERATURE = 0.1


class AzureOpenAIProvider(LLMProvider):
    name = "azure"

    def __init__(
        self,
        endpoint: str = "",
        api_key: str = "",
        api_version: str = "",
        client: openai.AsyncAzureOpenAI | None = None,
    ):
        self._client = client or openai.AsyncAzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version
        )

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        config: ReviewConfig,
    ) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                model=model,  # en Azure, el nombre del deployment
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "agent_report", "strict": True, "schema": schema},
                },
                temperature=TEMPERATURE,
                max_tokens=config.max_tokens,
            )
        except openai.BadRequestError as error:
            if getattr(error, "code", None) == "content_filter":
                raise LLMError("Azure bloqueó el prompt con su filtro de contenido") from error
            raise

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise LLMError("Azure bloqueó la respuesta con su filtro de contenido")
        if choice.finish_reason == "length":
            raise LLMError("la respuesta se cortó por max_tokens")
        if choice.message.refusal:
            raise LLMError(f"el modelo declinó la revisión: {choice.message.refusal}")
        if not choice.message.content:
            raise LLMError("la respuesta no tiene texto")
        usage = response.usage
        return LLMResponse(
            text=choice.message.content,
            model=response.model or model,
            usage=Usage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
        )
