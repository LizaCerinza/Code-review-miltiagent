---
# Guarda este archivo como .review-skills/<nombre>/SKILL.md en el repo objetivo.
# Se lee de la rama base del PR: los cambios a las skills se aplican después del merge.
name: nombre-en-kebab-case          # si coincide con una skill incluida, la reemplaza
agent: design                       # functional | security | design | all
description: Una línea que explica qué revisa esta skill
applies_to:                         # opcional: sin esta lista, la skill aplica a todos los PRs
  - "src/**/*.controller.ts"
  - "src/**/dto/**"
---
<!-- Instrucciones para el agente. Concretas y verificables: qué buscar, qué categoría y qué
     severidad usar, y qué NO reportar. Máximo 20 000 caracteres. -->

Reglas del equipo para los controllers:

- Cada endpoint documenta todas sus respuestas con decoradores de Swagger (`@ApiOkResponse`,
  `@ApiNotFoundResponse`, ...). Un endpoint sin la documentación de un código que puede devolver
  es un hallazgo `minor` con category `api-docs`.
- Los controllers no tienen lógica: solo llaman a un caso de uso y devuelven su resultado. Una
  condición o un cálculo en un controller es un hallazgo `major` con category `layering`.
- No reportes el orden de los decoradores: es una preferencia, no una regla.
