---
name: ci-workflows
agent: security
description: Seguridad de GitHub Actions, Dockerfiles y hooks
applies_to: [".github/**", "action.yml", "action.yaml", "Dockerfile", "**/Dockerfile", ".husky/**"]
---
Revisa los cambios en la cadena de CI/CD (category `ci-security`):
- `pull_request_target` o `workflow_run` que hacen checkout del código del PR y lo ejecutan
  (instalar dependencias, correr scripts o tests) con secrets disponibles: es `critical`.
- Expresiones `${{ github.event.* }}` (título, cuerpo o rama del PR) interpoladas directamente en
  `run:` (inyección de shell). Lo seguro es pasarlas por `env:`.
- `permissions` más amplios de lo necesario (`write-all`, `contents: write` sin motivo) o
  eliminación del bloque `permissions`.
- Actions de terceros referenciadas por rama (`@main`) en lugar de versión o SHA.
- Secrets impresos en logs, pasados como argumentos de línea de comandos o subidos como artefactos.
- Checks de calidad o seguridad removidos o con `continue-on-error: true`.
- Dockerfiles que corren como root, copian `.env` o secrets, o usan imágenes base sin versión.
