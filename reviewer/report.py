"""Markdown del comentario de resumen y de los comentarios inline."""

from __future__ import annotations

import re

from .models import AgentReport, Confidence, Finding, ReviewResult, Severity

SUMMARY_MARKER = "<!-- ai-review:summary -->"
FINGERPRINT_MARKER = "<!-- ai-review:fp={fp} -->"
# Límite de GitHub para un comentario: 65 536 caracteres. Se deja margen.
MAX_COMMENT_CHARS = 60_000

_SEVERITY_LABEL = {
    Severity.CRITICAL: "🔴 Critical",
    Severity.MAJOR: "🟠 Major",
    Severity.MINOR: "🟡 Minor",
    Severity.INFO: "🔵 Info",
}
_CONFIDENCE_LABEL = {Confidence.HIGH: "alta", Confidence.MEDIUM: "media", Confidence.LOW: "baja"}
_AGENT_LABEL = {"functional": "Funcional", "security": "Seguridad", "design": "Diseño"}


def fence(text: str, lang: str = "") -> str:
    """Bloque de código que no se rompe aunque el texto contenga ```."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text}\n{ticks}"


def location(finding: Finding) -> str:
    if not finding.file:
        return "General"
    return f"`{finding.file}:{finding.line}`" if finding.line else f"`{finding.file}`"


def verdict_line(result: ReviewResult) -> str:
    if result.blocking:
        text = "❌ **Bloqueante**: hay hallazgos que deben corregirse antes del merge."
    elif result.findings:
        text = "✅ **Sin bloqueos**: revisa los hallazgos de abajo."
    else:
        text = "✅ **Sin hallazgos.**"
    if result.incomplete:
        text += "\n\n⚠️ **Revisión incompleta**: al menos un agente no terminó (ver tabla)."
    return text


def agents_table(result: ReviewResult) -> str:
    rows = ["| Agente | Estado | Critical | Major | Minor | Info |", "|---|---|---|---|---|---|"]
    for report in result.reports:
        counts = {s: 0 for s in Severity}
        for finding in result.findings:
            if report.agent in finding.agents:
                counts[finding.severity] += 1
        status = "✅ ok" if report.status == "ok" else f"⚠️ error: {report.error}"
        name = _AGENT_LABEL.get(report.agent, report.agent)
        rows.append(f"| {name} | {status} | " + " | ".join(str(counts[s]) for s in Severity) + " |")
    return "\n".join(rows)


def agent_detail(report: AgentReport) -> str:
    lines = [f"**{_AGENT_LABEL.get(report.agent, report.agent)}**"]
    if report.skills:
        lines.append("Skills: " + ", ".join(f"`{s}`" for s in report.skills))
    if report.summary:
        lines.append(report.summary)
    return "\n\n".join(lines)


def finding_item(finding: Finding, detailed: bool) -> str:
    agents = ", ".join(_AGENT_LABEL.get(a, a) for a in finding.agents)
    header = (f"- **{finding.title}** · {location(finding)} · confianza "
              f"{_CONFIDENCE_LABEL[finding.confidence]} · {agents}")
    if finding.category:
        header += f" · `{finding.category}`"
    # Grave pero sin confianza alta: no bloquea, así que lo debe confirmar una persona.
    if finding.severity.rank <= Severity.MAJOR.rank and finding.confidence != Confidence.HIGH:
        header += " · ⚠️ requiere verificación humana"
    lines = [header, f"  {finding.message}"]
    if detailed:
        inner = [fence(finding.evidence)]
        if finding.suggestion:
            inner.append(f"**Sugerencia:** {finding.suggestion}")
        lines.append("  <details><summary>Evidencia y sugerencia</summary>\n\n"
                     + "\n\n".join(inner) + "\n\n  </details>")
    return "\n".join(lines)


def render_summary(result: ReviewResult, detailed: bool = True) -> str:
    parts = [SUMMARY_MARKER, "## 🤖 Code review multiagente", verdict_line(result),
             agents_table(result)]
    if result.notes:
        parts.append("**Notas**\n" + "\n".join(f"- {n}" for n in result.notes))

    if result.findings:
        parts.append("### Hallazgos")
        for severity in Severity:
            group = [f for f in result.findings if f.severity == severity]
            if group:
                parts.append(f"#### {_SEVERITY_LABEL[severity]} ({len(group)})")
                parts.append("\n".join(finding_item(f, detailed) for f in group))

    summaries = [r for r in result.reports if r.summary or r.skills]
    if summaries:
        body = "\n\n".join(agent_detail(r) for r in summaries)
        parts.append(f"<details><summary>Resumen de cada agente</summary>\n\n{body}\n\n</details>")

    threshold = "nunca bloquea (`fail-on: none`)" if result.fail_on == "none" else (
        f"bloquea con severidad `{result.fail_on}` o mayor y confianza alta")
    parts.append(f"<sub>Política: {threshold}.</sub>")
    text = "\n\n".join(parts)

    if detailed and len(text) > MAX_COMMENT_CHARS:
        compact = render_summary(result, detailed=False)
        return compact + ("\n\n<sub>La evidencia se omitió por el límite de tamaño del "
                          "comentario; está completa en el reporte JSON del job.</sub>")
    return text


def render_inline(finding: Finding) -> str:
    agents = ", ".join(_AGENT_LABEL.get(a, a) for a in finding.agents)
    parts = [
        f"**{_SEVERITY_LABEL[finding.severity]} · {finding.title}**",
        f"<sub>{agents} · confianza {_CONFIDENCE_LABEL[finding.confidence]}"
        + (f" · `{finding.category}`" if finding.category else "") + "</sub>",
        finding.message,
    ]
    if finding.suggestion:
        parts.append(f"**Sugerencia:** {finding.suggestion}")
    parts.append(FINGERPRINT_MARKER.format(fp=finding.fingerprint))
    return "\n\n".join(parts)
