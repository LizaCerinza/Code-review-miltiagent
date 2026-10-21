from reviewer.models import AgentReport, Confidence, Finding, ReviewResult, Severity


def make(**kw):
    base = {"file": "src/a.ts", "line": 10, "severity": "major", "title": "T", "message": "m"}
    base.update(kw)
    return Finding(**base)


def test_severity_and_confidence_order():
    ranks = [s.rank for s in (Severity.CRITICAL, Severity.MAJOR, Severity.MINOR, Severity.INFO)]
    assert ranks == sorted(ranks)
    assert Confidence.HIGH.rank < Confidence.MEDIUM.rank < Confidence.LOW.rank


def test_fingerprint_is_stable_and_normalizes_title():
    a = make(title="Endpoint  sin   guard")
    b = make(title="endpoint sin guard", severity="critical", message="otro")
    assert a.fingerprint == b.fingerprint
    assert len(a.fingerprint) == 12


def test_fingerprint_changes_with_location():
    assert make(line=10).fingerprint != make(line=11).fingerprint
    assert make(file="src/a.ts").fingerprint != make(file="src/b.ts").fingerprint


def test_agent_report_status():
    assert AgentReport(agent="design").status == "ok"
    assert AgentReport(agent="design", error="timeout").status == "error"


def test_review_result_failed():
    def result(**kw):
        base = {"reports": [], "findings": [], "fail_on": "critical",
                "blocking": False, "incomplete": False}
        base.update(kw)
        return ReviewResult(**base)

    assert result(blocking=True).failed
    assert not result(incomplete=True).failed
    assert result(incomplete=True, fail_on_agent_error=True).failed
