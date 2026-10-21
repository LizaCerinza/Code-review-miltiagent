---
name: supply-chain
agent: security
description: Dependencias nuevas o modificadas
applies_to: ["package.json", "**/package.json", ".npmrc", "**/.npmrc", "pyproject.toml", "requirements*.txt"]
---
Revisa cada dependencia agregada o cambiada (category `supply-chain`, CWE-1357):
- **Nombres inventados o parecidos a uno popular** (typosquatting / slopsquatting): una IA puede
  sugerir paquetes que no existen y que un atacante registra después. Señala cualquier nombre que
  no reconozcas como paquete conocido o que difiera por una letra de uno popular. Usa confidence
  `medium` salvo que estés seguro.
- Dependencias con scripts de instalación (`preinstall`, `postinstall`) o cambios en
  `allowScripts` / `.npmrc` que habiliten scripts.
- Versiones sin fijar (`*`, `latest`, URLs git o tarballs) en dependencias de producción.
- Dependencias que duplican una funcionalidad que el proyecto ya cubre.
- Paquetes de desarrollo movidos a dependencias de producción.
