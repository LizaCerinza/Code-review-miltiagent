---
name: test-coverage
agent: functional
description: Pruebas que verifican los criterios de la tarea
---
Cada criterio que se cumple pero no tiene en el PR un test que lo verifique (unitario o e2e) es un
hallazgo `minor` con category `missing-test`. En `suggestion` describe el test que falta (entrada,
acción y resultado esperado).

Un test cuenta solo si ejercita el comportamiento del criterio. Un test que solo verifica que se
llamó a un mock, o que se modificó para aceptar el comportamiento nuevo sin que la tarea lo pida,
no cuenta.
