"""Consolida los reportes de los agentes y decide el veredicto."""

from __future__ import annotations

import re
import unicodedata

from .models import AgentReport, Confidence, Finding, ReviewResult, Severity

# Duplicados entre agentes: mismo archivo, líneas cercanas y títulos parecidos.
# Calibrado con hallazgos reales: los duplicados dan >= 0.6 y los problemas distintos <= 0.34.
NEAR_LINES = 3
TITLE_SIMILARITY = 0.5
_STOPWORDS = {"del", "las", "los", "una", "uno", "para", "con", "sin", "que", "por", "como",
              "este", "esta", "falta", "directa", "directamente", "endpoint", "usa"}


def _title_tokens(title: str) -> set[str]:
    text = unicodedata.normalize("NFKD", title.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Prefijo de 5 letras como raíz aproximada: "valida" y "validación" cuentan igual.
    return {w[:5] for w in re.findall(r"[a-z0-9]+", text) if len(w) >= 3 and w not in _STOPWORDS}


def title_similarity(a: str, b: str) -> float:
    """Coeficiente de solapamiento entre las raíces de las palabras de dos títulos."""
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _same_problem(a: Finding, b: Finding) -> bool:
    """Dos agentes distintos describiendo el mismo problema con otras palabras."""
    return (
        a.file == b.file
        and abs(a.line - b.line) <= NEAR_LINES
        and not set(b.agents) <= set(a.agents)
        and title_similarity(a.title, b.title) >= TITLE_SIMILARITY
    )


def _merge(current: Finding, other: Finding) -> Finding:
    """Conserva el texto del más grave, la confianza más alta y todos los agentes."""
    winner = other if other.severity.rank < current.severity.rank else current
    confidence = min(current.confidence, other.confidence, key=lambda c: c.rank)
    agents = sorted(set(current.agents) | set(other.agents))
    return winner.model_copy(update={"confidence": confidence, "agents": agents})


def consolidate(findings: list[Finding]) -> list[Finding]:
    """Descarta hallazgos sin evidencia y une los duplicados.

    1. Misma huella (archivo, línea y título normalizado), de cualquier agente.
    2. Mismo problema reportado por agentes distintos (ver `_same_problem`).
    """
    by_fingerprint: dict[str, Finding] = {}
    for finding in findings:
        if not finding.evidence.strip():
            continue
        key = finding.fingerprint
        current = by_fingerprint.get(key)
        by_fingerprint[key] = finding.model_copy() if current is None else _merge(current, finding)

    # Del más grave al menos grave, para que el texto que queda sea el del hallazgo principal.
    merged: list[Finding] = []
    for finding in sorted(by_fingerprint.values(), key=lambda f: f.severity.rank):
        for index, current in enumerate(merged):
            if _same_problem(current, finding):
                merged[index] = _merge(current, finding)
                break
        else:
            merged.append(finding)
    return sorted(merged, key=lambda f: (f.severity.rank, f.file, f.line))


def is_blocking(finding: Finding, fail_on: str) -> bool:
    if fail_on == "none":
        return False
    return (
        finding.severity.rank <= Severity(fail_on).rank
        and finding.confidence == Confidence.HIGH
    )


def aggregate(
    reports: list[AgentReport],
    fail_on: str,
    fail_on_agent_error: bool = False,
    extra_findings: list[Finding] | None = None,
    notes: list[str] | None = None,
) -> ReviewResult:
    all_findings = [f for r in reports for f in r.findings] + list(extra_findings or [])
    findings = consolidate(all_findings)
    return ReviewResult(
        reports=reports,
        findings=findings,
        fail_on=fail_on,
        fail_on_agent_error=fail_on_agent_error,
        blocking=any(is_blocking(f, fail_on) for f in findings),
        incomplete=any(r.error for r in reports),
        notes=list(notes or []),
    )
