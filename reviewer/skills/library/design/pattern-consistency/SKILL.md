---
name: pattern-consistency
agent: design
description: Consistencia con los patrones que el repo ya usa
applies_to: ["src/**"]
---
El código nuevo debe resolver los problemas igual que el resto del repo (category
`pattern-consistency`). Antes de reportar, busca en los archivos mostrados y en <indice_repo> cómo
lo resuelve el repo, y nombra ese patrón en `message`:
- Errores de dominio + filtro de excepciones, frente a excepciones HTTP sueltas.
- Puerto (interfaz en `domain`) + adaptador (en `infrastructure`) + registro en el módulo con un
  token, frente a inyectar implementaciones concretas.
- Mappers entre entidad ORM y modelo de dominio, frente a devolver la entidad ORM.
- DTOs de entrada con `class-validator` y DTOs de respuesta documentados con Swagger.
- Casos de uso como clases con un único método `execute`.
- Nombres de archivos y clases (`*.use-case.ts`, `*.controller.ts`, `*.repository.port.ts`).
