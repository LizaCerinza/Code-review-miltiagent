"""Modelos compartidos por los agentes, el agregador y el publicador."""

from __future__ import annotations

import hashlib
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"

    @property
    def rank(self) -> int:
        """0 es lo más grave."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.INFO: 3}


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """0 es la confianza más alta."""
        return _CONFIDENCE_RANK[self]


_CONFIDENCE_RANK = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}


class Finding(BaseModel):
    file: str = Field("", description="Ruta del archivo; vacío = el PR en general")
    line: int = Field(0, description="Línea en la versión nueva del archivo; 0 = general")
    severity: Severity
    confidence: Confidence = Confidence.HIGH
    category: str = ""
    title: str
    message: str
    evidence: str = ""
    suggestion: str = ""
    agents: list[str] = Field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """Identifica el hallazgo entre ejecuciones para no comentar dos veces lo mismo."""
        key = f"{self.file}:{self.line}:{' '.join(self.title.lower().split())}"
        return hashlib.sha1(key.encode()).hexdigest()[:12]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class AgentReport(BaseModel):
    agent: str
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None
    model: str = ""
    usage: Usage = Field(default_factory=Usage)
    skills: list[str] = Field(default_factory=list)

    @property
    def status(self) -> str:
        return "error" if self.error else "ok"


class ReviewResult(BaseModel):
    reports: list[AgentReport]
    findings: list[Finding]
    fail_on: str
    fail_on_agent_error: bool = False
    blocking: bool
    incomplete: bool
    notes: list[str] = Field(default_factory=list)

    @property
    def failed(self) -> bool:
        """True si el proceso debe terminar con código de salida 1."""
        return self.blocking or (self.incomplete and self.fail_on_agent_error)
