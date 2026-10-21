---
name: config-secrets
agent: security
description: Configuración insegura y secretos
applies_to: ["src/config/**", "src/main.ts", "src/app.module.ts", "src/**/*.module.ts", ".env*", "**/.env*", "**/*.properties", "docker-compose*", "**/*.config.ts"]
---
Revisa la configuración (category `insecure-config`):
- `synchronize: true` de TypeORM que puede quedar activo en producción, o `dropSchema`.
- CORS abierto (`origin: '*'` o `true`) junto con credenciales.
- Defaults inseguros: secretos JWT o claves con valor por defecto, modo debug activo, puertos de
  administración expuestos, Swagger habilitado en producción sin protección.
- Secretos o credenciales escritos en el código o en archivos versionados (Sonar suele detectar
  los evidentes; busca los que llegan por defaults de configuración o por archivos de ejemplo con
  valores reales).
- Validación de variables de entorno eliminada o debilitada.
