---
name: weakened-controls
agent: security
description: Controles de seguridad o de calidad eliminados o desactivados
---
Busca cambios que desactivan controles existentes (category `weakened-control`). Una IA suele
hacerlo para que algo compile o pase los tests:
- Validaciones, guards, filtros o pipes eliminados o comentados.
- `eslint-disable`, `@ts-ignore`, `@ts-expect-error` o `any` agregados sobre código sensible.
- Tests eliminados, marcados con `.skip` / `.only`, o con aserciones debilitadas.
- Umbrales de cobertura, reglas de lint o Quality Gates relajados.
- Manejo de errores reemplazado por `catch` vacíos que ocultan fallos.
