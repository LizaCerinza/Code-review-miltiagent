from reviewer.models import AgentReport, Finding, ReviewResult
from reviewer.report import SUMMARY_MARKER, fence, render_inline, render_summary


def f(**kw):
    base = {"file": "src/a.ts", "line": 7, "severity": "critical", "confidence": "high",
            "category": "injection", "title": "SQL armado a mano", "message": "Se interpola.",
            "evidence": "query(`SELECT ${id}`)", "suggestion": "Usar parámetros.",
            "agents": ["security"]}
    base.update(kw)
    return Finding(**base)


def result(findings, **kw):
    base = {
        "reports": [AgentReport(agent="functional", summary="Criterio 1: cumple"),
                    AgentReport(agent="security"),
                    AgentReport(agent="design", error="superó el tiempo máximo de 600 s")],
        "findings": findings, "fail_on": "critical", "blocking": True, "incomplete": True,
        "notes": ["Contenido omitido por tamaño (revisado solo por diff): `src/big.ts`"],
    }
    base.update(kw)
    return ReviewResult(**base)


def test_summary_contains_verdict_agents_notes_and_findings():
    text = render_summary(result([f(), f(title="Duda", confidence="medium", line=9)]))
    assert text.startswith(SUMMARY_MARKER)
    assert "Bloqueante" in text
    assert "Revisión incompleta" in text
    assert "| Seguridad | ✅ ok | 2 | 0 | 0 | 0 |" in text
    assert "⚠️ error: superó el tiempo máximo" in text
    assert "src/big.ts" in text
    assert "`src/a.ts:7`" in text
    assert "requiere verificación humana" in text
    assert text.count("requiere verificación humana") == 1
    assert "Criterio 1: cumple" in text


def test_summary_without_findings():
    text = render_summary(result([], blocking=False, incomplete=False, notes=[]))
    assert "Sin hallazgos" in text
    assert "Hallazgos" not in text.split("Sin hallazgos")[1]


def test_summary_falls_back_to_compact_when_too_long():
    big = [f(title=f"t{i}", evidence="x" * 2_000) for i in range(40)]
    text = render_summary(result(big))
    assert len(text) < 65_536
    assert "reporte JSON" in text
    assert "<details><summary>Evidencia" not in text


def test_fence_survives_backticks():
    assert fence("a ``` b").startswith("````")


def test_inline_has_fingerprint_marker():
    finding = f()
    body = render_inline(finding)
    assert f"<!-- ai-review:fp={finding.fingerprint} -->" in body
    assert "SQL armado a mano" in body
