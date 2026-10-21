from __future__ import annotations

from ..context import ReviewContext
from .base import Agent


class FunctionalAgent(Agent):
    name = "functional"
    role_prompt = """
Eres el agente FUNCIONAL de un sistema de code review multiagente para backends NestJS.
Tu trabajo: verificar que el código del pull request implementa lo que pide la tarea \
(<tareas>) y no rompe las especificaciones vigentes del sistema (<especificaciones>).
No revises seguridad ni diseño: otros agentes se encargan.
"""

    def build_input(self, ctx: ReviewContext) -> str:
        return "\n\n".join(
            [
                "Revisa este pull request contra sus tareas y las especificaciones del sistema.",
                ctx.render_tasks(),
                ctx.render_specs(),
                ctx.render_pull_request(),
            ]
        )
