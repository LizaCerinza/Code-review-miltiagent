import json

from reviewer.agents import DesignAgent, FunctionalAgent, SecurityAgent, default_agents
from reviewer.agents.base import REPORT_SCHEMA
from reviewer.config import ReviewConfig
from reviewer.context import SONAR_OK, SONAR_UNAVAILABLE, ReviewContext
from reviewer.diff import ChangedFile
from reviewer.llm import LLMProvider, LLMResponse
from reviewer.tasks import TaskResolution


def ctx(**kw):
    base = {
        "title": "feat: roles",
        "description": "Implementa #roles",
        "files": [ChangedFile("src/a.ts", "modified", "@@ -1 +1 @@\n+x")],
        "tasks": TaskResolution(found={"docs/tasks/roles.md": "- Responder 409"}),
        "specs": {"openspec/specs/users/spec.md": "### Requirement: X"},
    }
    base.update(kw)
    return ReviewContext(**base)


def test_functional_input_has_tasks_specs_and_pr():
    text = FunctionalAgent().build_input(ctx())
    assert '<tarea path="docs/tasks/roles.md">' in text
    assert "<especificaciones>" in text
    assert "<diff>" in text


def test_functional_input_without_tasks():
    text = FunctionalAgent().build_input(ctx(tasks=TaskResolution()))
    assert "no referencia ninguna tarea" in text


def test_security_input_has_sonar_issues_and_unavailable_notice():
    issues = [{"rule": "S2068", "file": "src/a.ts", "line": 3, "message": "secret"}]
    text = SecurityAgent().build_input(ctx(sonar_issues=issues, sonar_status=SONAR_OK))
    assert "<sonar>" in text and "S2068" in text
    text = SecurityAgent().build_input(ctx(sonar_status=SONAR_UNAVAILABLE))
    assert "issues de Sonar no disponibles" in text


def test_design_input_notices_missing_guidelines():
    text = DesignAgent().build_input(ctx(guidelines="# Guías\n## Arquitectura\n"))
    assert "sin guías definidas" in text
    assert "<indice_repo>" in text
    text = DesignAgent().build_input(ctx(guidelines="# Guías\nLos casos de uso no usan Nest."))
    assert "Los casos de uso no usan Nest." in text


def test_default_agents_names():
    assert [a.name for a in default_agents()] == ["functional", "security", "design"]


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self):
        self.calls = []

    async def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return LLMResponse(text=json.dumps({"summary": "ok", "findings": []}), model="m")


async def test_run_sends_prompt_schema_and_agent_model():
    provider = FakeProvider()
    config = ReviewConfig(agent_models={"design": "gpt-4.1"})

    report = await DesignAgent().run(provider, ctx(), config)

    assert report.agent == "design" and report.findings == []
    sent = provider.calls[0]
    assert sent["model"] == "gpt-4.1"
    assert sent["schema"] == REPORT_SCHEMA
    assert "Datos no confiables" in sent["system"]
    assert "<indice_repo>" in sent["user"]
