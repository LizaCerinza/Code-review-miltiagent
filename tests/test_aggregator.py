from reviewer.aggregator import aggregate, consolidate
from reviewer.models import AgentReport, Finding


def f(**kw):
    base = {"file": "src/users.controller.ts", "line": 42, "severity": "major",
            "confidence": "high", "title": "Problema", "message": "m", "evidence": "codigo",
            "agents": ["security"]}
    base.update(kw)
    return Finding(**base)


def test_findings_without_evidence_are_dropped():
    assert consolidate([f(evidence="   ")]) == []


def test_duplicates_merge_keeping_highest_severity_and_all_agents():
    merged = consolidate([
        f(severity="major", agents=["security"]),
        f(severity="minor", confidence="medium", agents=["design"], message="otro"),
    ])
    assert len(merged) == 1
    assert merged[0].severity.value == "major"
    assert merged[0].confidence.value == "high"
    assert merged[0].agents == ["design", "security"]


def test_sorted_by_severity_then_location():
    out = consolidate([f(title="b", severity="minor"), f(title="a", severity="critical", line=1)])
    assert [x.title for x in out] == ["a", "b"]


def test_critical_high_confidence_blocks():
    report = AgentReport(agent="security", findings=[f(severity="critical")])
    result = aggregate([report], "critical")
    assert result.blocking and result.failed


def test_critical_medium_confidence_does_not_block():
    finding = f(severity="critical", confidence="medium")
    result = aggregate([AgentReport(agent="security", findings=[finding])], "critical")
    assert not result.blocking
    assert result.findings == [finding]


def test_threshold_major_and_none():
    reports = [AgentReport(agent="design", findings=[f(severity="major")])]
    assert not aggregate(reports, "critical").blocking
    assert aggregate(reports, "major").blocking
    critical = [AgentReport(agent="d", findings=[f(severity="critical")])]
    assert not aggregate(critical, "none").blocking


def test_agent_error_marks_incomplete_without_failing_by_default():
    reports = [AgentReport(agent="functional"), AgentReport(agent="security", error="timeout")]
    result = aggregate(reports, "critical")
    assert result.incomplete and not result.blocking and not result.failed
    assert aggregate(reports, "critical", fail_on_agent_error=True).failed


def test_extra_findings_count_for_verdict():
    extra = [f(severity="critical", agents=["functional"])]
    result = aggregate([], "critical", extra_findings=extra)
    assert result.blocking
