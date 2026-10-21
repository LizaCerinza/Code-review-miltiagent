"""Grafo de LangGraph que ejecuta los agentes en paralelo y consolida sus resultados.

    START ──┬──► functional ──┐
            ├──► security   ──┼──► aggregate ──► END
            └──► design     ──┘
"""

from __future__ import annotations

import asyncio
import logging
import operator
import os
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import Agent, default_agents
from .aggregator import aggregate
from .config import ReviewConfig
from .context import SONAR_UNAVAILABLE, ReviewContext
from .llm import LLMProvider, create_provider
from .models import AgentReport, Confidence, Finding, ReviewResult, Severity

log = logging.getLogger(__name__)

AGGREGATE_NODE = "aggregate"


class ReviewState(TypedDict):
    ctx: ReviewContext
    # Reducer operator.add: cada agente agrega su reporte sin pisar el de los demás.
    reports: Annotated[list[AgentReport], operator.add]
    result: ReviewResult | None


async def run_agent(
    agent: Agent, provider: LLMProvider, ctx: ReviewContext, config: ReviewConfig
) -> AgentReport:
    """Ejecuta un agente; cualquier fallo se convierte en un reporte con error."""
    try:
        return await asyncio.wait_for(
            agent.run(provider, ctx, config), timeout=config.agent_timeout
        )
    except asyncio.TimeoutError:
        error = f"superó el tiempo máximo de {config.agent_timeout:.0f} s"
    except Exception as exc:  # frontera del agente: el resto de la revisión debe seguir
        error = f"{type(exc).__name__}: {exc}"
    log.warning("El agente %s falló: %s", agent.name, error)
    return AgentReport(agent=agent.name, error=error, model=config.model_for(agent.name))


def task_findings(ctx: ReviewContext, tasks_dir: str) -> list[Finding]:
    """Hallazgos de tarea ausente o inexistente, generados sin llamar al modelo."""
    if not ctx.tasks.referenced:
        excerpt = (ctx.description or "").strip()[:300] or "(descripción vacía)"
        return [
            Finding(
                severity=Severity.CRITICAL,
                confidence=Confidence.HIGH,
                category="missing-task",
                title="PR sin tarea referenciada",
                message=(
                    "El título y la descripción del PR no referencian ninguna tarea. Agrega un "
                    f"hashtag con el nombre del archivo de la tarea (por ejemplo `#mi-tarea` para "
                    f"`{tasks_dir}/mi-tarea.md`) para que se pueda validar la funcionalidad."
                ),
                evidence=f"Título: {ctx.title}\nDescripción: {excerpt}",
                agents=["functional"],
            )
        ]
    return [
        Finding(
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            category="missing-task",
            title=f"Tarea #{name} no encontrada",
            message=f"El PR referencia `#{name}`, pero no existe `{path}`.",
            evidence=f"#{name}",
            suggestion=f"Crea `{path}` o corrige el hashtag en la descripción del PR.",
            agents=["functional"],
        )
        for name, path in ctx.tasks.missing
    ]


def context_notes(ctx: ReviewContext) -> list[str]:
    notes = []
    if ctx.omitted:
        notes.append("Contenido omitido por tamaño (revisado solo por diff): "
                     + ", ".join(f"`{p}`" for p in ctx.omitted))
    if ctx.sonar_status == SONAR_UNAVAILABLE:
        notes.append("Issues de Sonar no disponibles: el agente de seguridad no pudo descartar "
                     "duplicados de Sonar.")
    if not ctx.has_guidelines:
        notes.append(f"Sin guías definidas (`{ctx.guidelines_file}`): el agente de diseño usó "
                     "las convenciones del código.")
    if ctx.tasks.found:
        notes.append("Tareas validadas: " + ", ".join(f"`{p}`" for p in ctx.tasks.found))
    notes.extend(ctx.skill_notes)
    return notes


def build_graph(config: ReviewConfig, provider: Any, agents: list[Agent]) -> Any:
    """Compila el grafo: un nodo por agente en paralelo desde START y un nodo `aggregate`."""
    order = [agent.name for agent in agents]

    def agent_node(agent: Agent):
        async def node(state: ReviewState) -> dict[str, Any]:
            return {"reports": [await run_agent(agent, provider, state["ctx"], config)]}
        return node

    async def aggregate_node(state: ReviewState) -> dict[str, Any]:
        # Los reportes llegan en el orden en que terminan; se ordenan para un resultado estable.
        reports = sorted(state["reports"], key=lambda r: order.index(r.agent))
        result = aggregate(
            reports,
            fail_on=config.fail_on,
            fail_on_agent_error=config.fail_on_agent_error,
            extra_findings=task_findings(state["ctx"], config.tasks_dir),
            notes=context_notes(state["ctx"]),
        )
        return {"result": result}

    graph = StateGraph(ReviewState)
    graph.add_node(AGGREGATE_NODE, aggregate_node)
    for agent in agents:
        graph.add_node(agent.name, agent_node(agent))
        graph.add_edge(START, agent.name)
        graph.add_edge(agent.name, AGGREGATE_NODE)
    if not agents:
        graph.add_edge(START, AGGREGATE_NODE)
    graph.add_edge(AGGREGATE_NODE, END)
    return graph.compile(name="code-review-multiagente")


def graph_mermaid(agents: list[Agent] | None = None) -> str:
    """Diagrama Mermaid del grafo (para la documentación)."""
    agents = agents if agents is not None else default_agents()
    return build_graph(ReviewConfig(), None, agents).get_graph().draw_mermaid()


async def review(
    ctx: ReviewContext,
    config: ReviewConfig,
    provider: LLMProvider | None = None,
    agents: list[Agent] | None = None,
) -> ReviewResult:
    agents = agents if agents is not None else default_agents()
    provider = provider or create_provider(config, os.environ)
    graph = build_graph(config, provider, agents)
    state = await graph.ainvoke({"ctx": ctx, "reports": [], "result": None})
    return state["result"]
