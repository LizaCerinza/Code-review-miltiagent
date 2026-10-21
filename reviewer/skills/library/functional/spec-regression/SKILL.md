---
name: spec-regression
agent: functional
description: Regresiones contra las especificaciones vigentes del sistema
---
Las especificaciones de <especificaciones> describen el comportamiento vigente (requisitos con
escenarios WHEN/THEN). Un cambio del PR que contradice un requisito o escenario vigente, y que la
tarea no pide modificar explícitamente, es un hallazgo `critical` con category `spec-regression`.

Compara sobre todo: rutas y métodos HTTP, códigos de respuesta, validaciones de entrada, reglas
de unicidad o existencia y forma de los datos devueltos. Cita el requisito (archivo y nombre) en
`message`.

Si la tarea pide cambiar un comportamiento especificado, no es regresión; en ese caso indica en
`summary` que el spec debe actualizarse.
