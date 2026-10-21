"""Consolida los reportes de los agentes y decide el veredicto."""

from __future__ import annotations

from .models import AgentReport, Confidence, Finding, ReviewResult, Severity


def consolidate(findings: list[Finding]) -> list[Finding]:
    """Descarta hallazgos sin evidencia y une los duplicados (misma huella).

    El hallazgo resultante conserva la severidad más alta, la confianza más alta y la
    lista de todos los agentes que lo reportaron.
    """
    merged: dict[str, Finding] = {}
    for finding in findings:
        if not finding.evidence.strip():
            continue
        key = finding.fingerprint
        current = merged.get(key)
        if current is None:
            merged[key] = finding.model_copy()
            continue
        winner = finding if finding.severity.rank < current.severity.rank else current
        confidence = min(current.confidence, finding.confidence, key=lambda c: c.rank)
        agents = sorted(set(current.agents) | set(finding.agents))
        merged[key] = winner.model_copy(update={"confidence": confidence, "agents": agents})
    return sorted(merged.values(), key=lambda f: (f.severity.rank, f.file, f.line))


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
