---
name: reuse-and-simplicity
agent: design
description: Duplicación, código muerto, sobreingeniería y responsabilidades
---
- **Duplicación** (category `duplication`): lógica que ya existe en el repo. Usa <indice_repo> y los
  archivos mostrados para nombrar la implementación existente en `message`.
- **Código muerto** (category `dead-code`): funciones, clases, parámetros o configuración que
  nada usa; imports o ramas inalcanzables.
- **Sobreingeniería** (category `over-engineering`, normalmente `minor`): interfaces con una sola
  implementación que nada necesita abstraer, factories o capas extra para un caso simple,
  configuración que nada lee.
- **Responsabilidad única y acoplamiento** (category `single-responsibility` o `coupling`): clases o
  casos de uso que hacen varias cosas no relacionadas (crear un usuario, enviar un email y
  auditar), o dependencias de implementaciones concretas donde el proyecto usa puertos.
