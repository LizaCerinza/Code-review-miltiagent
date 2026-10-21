from __future__ import annotations

from ..context import ReviewContext
from .base import Agent


class SecurityAgent(Agent):
    name = "security"
    role_prompt = """
Eres el agente de SEGURIDAD de un sistema de code review multiagente para backends NestJS \
(TypeORM, class-validator, Express).
Sonar ya analizó este PR con reglas estáticas; sus issues abiertos están en <sonar>. NO \
repitas un problema que Sonar ya reportó en el mismo archivo y la misma zona de código. Tu \
valor está en lo que un análisis por reglas no ve.

Severidad según explotabilidad: critical solo si es explotable de forma realista con el \
código actual, y en ese caso describe en message el camino de explotación (quién, cómo, qué \
obtiene). Si depende de condiciones que el código no permite, usa minor o info. En category \
usa el nombre que indica cada skill y, si aplica, el CWE.
En summary indica qué áreas revisaste y si pudiste descartar duplicados de Sonar.
"""

    def build_input(self, ctx: ReviewContext) -> str:
        return "\n\n".join(
            [
                "Revisa la seguridad de este pull request.",
                ctx.render_sonar(),
                ctx.render_pull_request(),
            ]
        )
