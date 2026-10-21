---
name: scope-and-claims
agent: functional
description: Alcance del cambio y afirmaciones de la descripción del PR
---
**Alcance.** Todo cambio de comportamiento que ninguna tarea justifica es un hallazgo `major` con
category `out-of-scope`: endpoints, validaciones o respuestas existentes que cambian, lógica
nueva no pedida, renombres de rutas o campos. Los refactors sin cambio de comportamiento no son
hallazgos funcionales.

**Afirmaciones.** Revisa la descripción del PR (<pull_request>). Cada afirmación sobre lo
implementado o probado que el diff no respalda es un hallazgo `major` con category
`unsupported-claim`. Ejemplos: "agregué tests para X" sin tests de X en el diff, "maneja el caso
de email duplicado" sin código para ese caso. Cita la afirmación en `evidence`.
