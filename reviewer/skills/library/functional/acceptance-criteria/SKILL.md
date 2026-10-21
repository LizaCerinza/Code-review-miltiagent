---
name: acceptance-criteria
agent: functional
description: Validación de los criterios de aceptación de la tarea
---
Identifica cada requisito o criterio de aceptación de cada tarea de <tareas> y clasifícalo:
- **cumple**: el código del PR lo implementa y puedes señalar el archivo y la línea. Lo que diga
  la descripción del PR no cuenta como prueba.
- **no cumple**: el código no lo implementa, o lo implementa distinto (otro código HTTP, otra
  validación, otro dato devuelto). Es un hallazgo con category `unmet-criterion`; usa severity
  `critical` si cambia el comportamiento observable de la API.
- **no verificable**: depende de código que no está en el PR ni en su contexto. No es un hallazgo.

En `summary` lista cada criterio con su estado. Cita el criterio en `message` y el código
responsable en `evidence`.

Si no hay tareas (el bloque <tareas> lo indica), no inventes criterios: otro componente ya
reporta la falta de tarea.
