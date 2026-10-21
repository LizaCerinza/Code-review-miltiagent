---
name: api-contracts
agent: design
description: Cambios en contratos públicos y compatibilidad
applies_to: ["src/**/*.controller.ts", "src/**/*.dto.ts", "src/**/dto/**", "src/**/*.port.ts", "src/**/domain/**"]
---
Reporta los cambios que rompen contratos públicos sin que la descripción del PR o su tarea lo
justifique (category `breaking-change`):
- Rutas, métodos HTTP o códigos de respuesta que cambian en endpoints existentes.
- Campos eliminados, renombrados o con otro tipo en DTOs de entrada o de respuesta.
- Firmas de puertos de dominio que cambian y obligan a modificar todos sus adaptadores.
- Documentación de Swagger (`@ApiOkResponse`, `@ApiProperty`) que deja de coincidir con lo que
  el endpoint realmente devuelve.
