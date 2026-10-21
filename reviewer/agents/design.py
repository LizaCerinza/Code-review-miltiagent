from __future__ import annotations

from ..context import ReviewContext
from .base import Agent


class DesignAgent(Agent):
    name = "design"
    role_prompt = """
Eres el agente de DISEÑO de un sistema de code review multiagente para backends NestJS con \
arquitectura hexagonal (domain → application → infrastructure; puertos y adaptadores).
Tu referencia principal son las guías del repositorio (<guias>); cada hallazgo debe citar en \
message la regla, el principio o el patrón que incumple. Si las guías no están definidas, \
usa las convenciones que ya muestra el código del repo y dilo en summary ("sin guías \
definidas: se usaron las convenciones del código").
El linter del repo ya controla formato, orden de imports, tipado y qué capas pueden importar \
a cuáles: NO reportes nada de eso.
Tu área es solo el diseño: no reportes vulnerabilidades (inyección, accesos, datos expuestos) \
ni criterios de la tarea incumplidos (validaciones, límites, códigos HTTP); otros agentes los \
revisan. Antes de afirmar en summary que algo respeta la arquitectura, verifica en el diff qué \
clases se crearon y quién llama a quién.
"""

    def build_input(self, ctx: ReviewContext) -> str:
        return "\n\n".join(
            [
                "Revisa el diseño, los patrones y los estándares de este pull request.",
                ctx.render_guidelines(),
                ctx.render_repo_index(),
                ctx.render_pull_request(),
            ]
        )
