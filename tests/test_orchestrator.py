import asyncio

from reviewer.agents.base import Agent
from reviewer.config import ReviewConfig
from reviewer.context import ReviewContext
from reviewer.models import AgentReport, Finding
from reviewer.orchestrator import build_graph, graph_mermaid, review
from reviewer.tasks import TaskResolution


class FakeAgent(Agent):
    role_prompt = ""

    def __init__(self, name, behavior):
        self.name = name
        self.behavior = behavior

    def build_input(self, ctx):
        return ""

    async def run(self, provider, ctx, config):
        if self.behavior == "fail":
            raise RuntimeError("API caída")
        if self.behavior == "slow":
            await asyncio.sleep(5)
        if self.behavior == "slow-ok":
            await asyncio.sleep(0.2)
        finding = Finding(file="src/a.ts", line=1, severity="minor", title=f"de {self.name}",
                          message="m", evidence="x", agents=[self.name])
        return AgentReport(agent=self.name, summary="ok", findings=[finding])


def ctx(tasks=None, description="Implementa #t"):
    return ReviewContext(
        title="T", description=description, files=[],
        tasks=tasks if tasks is not None else TaskResolution(found={"docs/tasks/t.md": "x"}),
        guidelines="# G\nregla",
    )


async def test_failing_and_slow_agents_do_not_block_the_others():
    agents = [FakeAgent("functional", "ok"), FakeAgent("security", "fail"),
              FakeAgent("design", "slow")]
    result = await review(ctx(), ReviewConfig(agent_timeout=0.2), provider=object(), agents=agents)

    by_name = {r.agent: r for r in result.reports}
    assert by_name["functional"].status == "ok"
    assert by_name["security"].error == "RuntimeError: API caída"
    assert "tiempo máximo" in by_name["design"].error
    assert [f.title for f in result.findings] == ["de functional"]
    assert result.incomplete and not result.failed


async def test_missing_task_generates_critical_without_model():
    result = await review(ctx(tasks=TaskResolution(), description="Arregla cosas"),
                          ReviewConfig(), provider=object(), agents=[])
    assert result.blocking
    finding = result.findings[0]
    assert finding.category == "missing-task"
    assert finding.title == "PR sin tarea referenciada"
    assert "Arregla cosas" in finding.evidence
    assert "docs/tasks/mi-tarea.md" in finding.message


async def test_unresolved_task_names_the_path():
    tasks = TaskResolution(missing=[("tarea-x", "docs/tasks/tarea-x.md")])
    result = await review(ctx(tasks=tasks), ReviewConfig(), provider=object(), agents=[])
    assert result.findings[0].title == "Tarea #tarea-x no encontrada"
    assert "docs/tasks/tarea-x.md" in result.findings[0].message
    assert result.blocking


def test_graph_fans_out_from_start_and_joins_in_aggregate():
    agents = [FakeAgent("functional", "ok"), FakeAgent("security", "ok"),
              FakeAgent("design", "ok")]
    graph = build_graph(ReviewConfig(), object(), agents).get_graph()
    edges = {(e.source, e.target) for e in graph.edges}
    for name in ("functional", "security", "design"):
        assert ("__start__", name) in edges
        assert (name, "aggregate") in edges
    assert ("aggregate", "__end__") in edges


def test_reports_keep_agent_order_regardless_of_finish_time():
    agents = [FakeAgent("functional", "slow-ok"), FakeAgent("security", "ok")]
    result = asyncio.run(review(ctx(), ReviewConfig(), provider=object(), agents=agents))
    assert [r.agent for r in result.reports] == ["functional", "security"]


def test_mermaid_diagram_lists_the_agents():
    text = graph_mermaid()
    for name in ("functional", "security", "design", "aggregate"):
        assert name in text
