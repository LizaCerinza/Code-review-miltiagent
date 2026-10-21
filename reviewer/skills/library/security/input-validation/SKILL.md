---
name: input-validation
agent: security
description: Validación de entrada y asignación masiva (class-validator, TypeORM)
applies_to: ["src/**"]
---
Busca datos de la petición que llegan a la lógica o a la persistencia sin validar:
- DTOs nuevos o modificados sin decoradores de `class-validator` en algún campo, o con
  restricciones más débiles que antes (category `input-validation`).
- `ValidationPipe` sin `whitelist` / `forbidNonWhitelisted`, o con esas opciones removidas.
- **Asignación masiva (CWE-915)**: el body o un objeto parcial se copia directo sobre una entidad
  (`Object.assign(entity, dto)`, spread, `repository.save({...body})`) y la entidad tiene campos
  que el cliente no debería controlar (`role`, `isAdmin`, `ownerId`, timestamps). Category
  `mass-assignment`.
- `null` o `undefined` que pasan la validación (por ejemplo, con `@IsOptional`) y llegan a
  columnas obligatorias, produciendo errores 500 o datos inconsistentes.
- Parámetros de ruta usados sin `ParseUUIDPipe` / `ParseIntPipe` donde el repo sí los usa.
