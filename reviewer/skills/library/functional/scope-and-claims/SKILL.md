---
name: scope-and-claims
agent: functional
description: Alcance del cambio y afirmaciones de la descripción del PR
---
**Afirmaciones: verifícalas una por una.** La descripción del PR (<pull_request>) y los mensajes
de commit son afirmaciones de quien hizo el cambio, no evidencia. Haz este procedimiento:

1. Lista cada frase que afirma algo sobre lo implementado o probado. Por ejemplo: "valida el
   parámetro", "limita los resultados", "incluye tests unitarios y e2e", "maneja el caso X".
2. Para cada una, busca en <diff> el código o el test concreto que la cumple.
3. Si no lo encuentras, es un hallazgo `major` con category `unsupported-claim`. En `evidence`
   cita la frase de la descripción; en `message` explica qué buscaste y no está (por ejemplo:
   "el diff no agrega ningún archivo `*.spec.ts` ni `*.e2e-spec.ts`").

Nunca uses la descripción para decidir que un criterio "cumple": decide solo con el código.

**Alcance.** Todo cambio de comportamiento que ninguna tarea justifica es un hallazgo `major` con
category `out-of-scope`: endpoints, validaciones o respuestas existentes que cambian, lógica
nueva no pedida, renombres de rutas o campos. Los refactors sin cambio de comportamiento no son
hallazgos funcionales.
