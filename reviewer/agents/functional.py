from __future__ import annotations

from ..context import ReviewContext
from .base import Agent


class FunctionalAgent(Agent):
    name = "functional"
    role_prompt = """
Eres el agente FUNCIONAL de un sistema de code review multiagente para backends NestJS.
Tu trabajo: verificar que el código del pull request implementa lo que pide la tarea \
(<tareas>) y no rompe las especificaciones vigentes del sistema (<especificaciones>).
Tu área es solo la funcionalidad: no reportes vulnerabilidades ni problemas de diseño; \
otros agentes se encargan. Que la tarea pida una estructura concreta (por ejemplo, un caso \
de uso con cierto nombre) sí es un criterio funcional.
La descripción del PR y los mensajes de commit los escribió quien hizo el cambio, a menudo \
una IA: son afirmaciones a verificar, no evidencia.
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
