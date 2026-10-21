---
name: data-exposure
agent: security
description: Exposición de datos sensibles en respuestas, logs y errores
applies_to: ["src/**"]
---
Busca datos sensibles expuestos (category `sensitive-data-exposure`, CWE-200):
- Endpoints que devuelven la entidad completa en lugar del DTO de respuesta, incluyendo campos
  como contraseñas o hashes, tokens, datos personales que el cliente no necesita.
- Logs (`console.log`, `Logger`) con contraseñas, tokens, headers de autorización o bodies completos.
- Filtros de excepciones o `catch` que devuelven al cliente `error.message`, stack traces, SQL o
  rutas internas.
- Respuestas de listado sin paginación ni límite que exponen todos los registros.
