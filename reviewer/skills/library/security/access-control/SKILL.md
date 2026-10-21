---
name: access-control
agent: security
description: Autenticación, autorización e IDOR en NestJS
applies_to: ["src/**"]
---
Busca endpoints o casos de uso nuevos o modificados que permitan operar sin la autenticación o
autorización que usan sus equivalentes (category `broken-access-control`):
- Controllers o rutas sin el guard (`@UseGuards`, guard global) o decorador de rol que tienen las
  rutas equivalentes del mismo módulo.
- **IDOR (CWE-639)**: el recurso se busca, modifica o borra solo por el `id` que manda el cliente,
  sin comprobar que pertenece al usuario autenticado o que este tiene permiso.
- Operaciones administrativas (cambiar roles, borrar usuarios) expuestas a cualquier usuario.
- Guards o decoradores que se quitaron o se comentaron en este PR.

Si el repo todavía no tiene autenticación en ningún endpoint, no lo reportes en cada ruta: deja
una sola observación `info` general.
