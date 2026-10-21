from reviewer.aggregator import aggregate, consolidate, evidence_similarity, title_similarity
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


# ---- duplicados entre agentes (títulos reales de la primera prueba con gpt-4.1-mini) --------

def test_same_problem_from_different_agents_is_merged():
    merged = consolidate([
        f(file="repo.ts", line=49, severity="critical", agents=["security"],
          title="Inyección SQL en consulta LIKE con interpolación directa del parámetro 'term'"),
        f(file="repo.ts", line=49, severity="critical", agents=["design"],
          title="Consulta SQL vulnerable a inyección SQL en searchByName"),
        f(file="ctrl.ts", line=54, severity="critical", agents=["functional"],
          title="No se valida que el parámetro q esté presente y no vacío"),
        f(file="ctrl.ts", line=52, severity="major", agents=["design"],
          title="Falta validación del parámetro 'q' en el controller para responder 400"),
        f(file="ctrl.ts", line=53, severity="major", agents=["security"],
          title="Falta validación del parámetro 'q' en el endpoint de búsqueda"),
    ])
    assert [(x.file, x.severity.value, x.agents) for x in merged] == [
        ("ctrl.ts", "critical", ["design", "functional", "security"]),
        ("repo.ts", "critical", ["design", "security"]),
    ]
    assert merged[0].title == "No se valida que el parámetro q esté presente y no vacío"


def test_different_problems_of_the_same_agent_are_kept():
    merged = consolidate([
        f(file="ctrl.ts", line=54, agents=["functional"],
          title="Falta caso de uso SearchUsersUseCase para la búsqueda de usuarios"),
        f(file="ctrl.ts", line=54, agents=["functional"],
          title="No se valida que el parámetro q esté presente y no vacío"),
        f(file="ctrl.ts", line=54, agents=["functional"],
          title="No se limita la cantidad máxima de usuarios devueltos a 20"),
    ])
    assert len(merged) == 3


def test_similar_titles_far_apart_or_in_other_files_are_kept():
    a = f(file="ctrl.ts", line=10, agents=["security"], title="Falta validación del parámetro q")
    far = f(file="ctrl.ts", line=40, agents=["design"], title="Falta validación del parámetro q")
    other = f(file="dto.ts", line=10, agents=["design"], title="Falta validación del parámetro q")
    assert len(consolidate([a, far])) == 2
    assert len(consolidate([a, other])) == 2


def test_title_similarity_ignores_accents_and_word_forms():
    assert title_similarity("No se valida el parámetro", "Falta validación del parametro") >= 0.5
    assert title_similarity("Inyección SQL", "Ordenamiento de resultados") == 0.0


# ---- duplicados por evidencia (citas reales de la segunda prueba) ---------------------------

SQL = "const rows = await this.orm.query(\n  `SELECT * FROM users WHERE name LIKE '%${term}%'`,\n);"
METHOD = ("async search(@Query('q') q: string): Promise<User[]> {\n"
          "  const term = (q ?? '').trim().toLowerCase();\n"
          "  const found = await this.users.searchByName(term);\n"
          "  return found.sort((a, b) => a.name.localeCompare(b.name));\n}")


def test_same_quoted_code_from_different_agents_is_merged():
    merged = consolidate([
        f(file="repo.ts", line=49, severity="critical", agents=["security"], evidence=SQL,
          title="Inyección SQL en búsqueda de usuarios por nombre"),
        f(file="repo.ts", line=48, severity="major", agents=["design", "functional"],
          evidence="  " + SQL.replace("\n", "\n    "),
          title="Consulta SQL en searchByName no usa parámetros parametrizados"),
    ])
    assert len(merged) == 1
    assert merged[0].severity.value == "critical"
    assert merged[0].agents == ["design", "functional", "security"]


def test_different_problems_quoting_the_same_method_are_kept():
    """Ambos citan el método search, pero uno es la validación de q y el otro las capas."""
    merged = consolidate([
        f(file="ctrl.ts", line=51, severity="critical", agents=["functional"], evidence=METHOD,
          title="No valida que el parámetro 'q' esté presente y no vacío"),
        f(file="ctrl.ts", line=54, severity="major", agents=["design"],
          evidence="@Get('search')\n@ApiOkResponse({ type: UserResponseDto, isArray: true })\n"
          + METHOD,
          title="Controller llama directamente al repositorio en lugar de usar un caso de uso"),
    ])
    assert len(merged) == 2
    assert evidence_similarity(merged[0].evidence, merged[1].evidence) < 0.85


def test_positive_findings_are_dropped():
    """gpt-5-mini publicó un `info` con categoría `cumple-evidence` para un criterio cumplido."""
    merged = consolidate([
        f(severity="info", category="cumple-evidence", title="Búsqueda insensible a mayúsculas"),
        f(severity="info", category="OK", title="Todo bien", line=20),
        f(severity="minor", category="missing-test", title="Falta test", line=30),
    ])
    assert [x.category for x in merged] == ["missing-test"]
