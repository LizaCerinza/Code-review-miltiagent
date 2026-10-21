"""Interfaz común de los proveedores de modelos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..config import ReviewConfig
from ..models import Usage


class LLMError(RuntimeError):
    """El proveedor no devolvió una respuesta utilizable (rechazo, filtro, truncado...)."""


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Usage = field(default_factory=Usage)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        config: ReviewConfig,
    ) -> LLMResponse:
        """Devuelve un texto JSON que cumple `schema` (salida estructurada del proveedor)."""
