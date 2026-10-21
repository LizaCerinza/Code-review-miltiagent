# Proposal

## Why

Los pull requests de los proyectos NestJS objetivo (como `farsov/Code-review-miltiagent`) ya pasan lint, tests y Sonar, pero esas herramientas no responden tres preguntas: ¿el cambio hace lo que pedía la tarea?, ¿abre un problema de seguridad que un analizador por reglas no ve?, ¿respeta la arquitectura y los estándares del equipo? Además, la mayoría de esos PRs los escribe una IA. Ese código suele verse plausible y aun así contener lógica incorrecta, cambios fuera del alcance, dependencias inventadas o duplicación, y un revisor humano no siempre lo detecta.

## What Changes

- Nuevo proyecto Python (este repositorio) con un revisor multiagente que se ejecuta como CLI (`python -m reviewer`) y como GitHub Action compuesta.
- Un orquestador recoge el contexto del PR: diff, archivos cambiados, tarea, especificaciones, guías e issues de Sonar. Luego ejecuta en paralelo tres subagentes especializados, orquestados como un grafo de LangGraph, une sus hallazgos y emite un veredicto.
- **Agente funcional**: valida el PR contra la tarea en `.md` que el PR referencia con un hashtag (`#<nombre-del-archivo>`) y contra las especificaciones del repo. Detecta requisitos incumplidos, cambios fuera del alcance de la tarea y afirmaciones de la descripción del PR que el diff no respalda.
- **Agente de seguridad**: busca vulnerabilidades que Sonar no detecta (autorización, IDOR, lógica de negocio explotable, exposición de datos, cambios inseguros en CI, dependencias inexistentes o sospechosas, prompt injection) sin repetir los issues que Sonar ya reportó en el PR.
- **Agente de diseño**: verifica patrones y estándares (arquitectura hexagonal, SOLID, convenciones de NestJS y el `REVIEW_GUIDELINES.md` del repo objetivo), centrado en lo que ESLint no cubre.
- Publicación en el PR: un comentario de resumen que se actualiza en cada ejecución, comentarios inline sin duplicados y un código de salida que bloquea el merge cuando hay hallazgos críticos de alta confianza.
- Reglas transversales para PRs escritos por IA: el contenido del PR se trata siempre como datos y nunca como instrucciones; cada hallazgo exige evidencia citada y declara su nivel de confianza.
- Skills de revisión: el conocimiento de cada agente se organiza en archivos `SKILL.md` que el revisor selecciona según los archivos que cambia el PR. Cada repo objetivo puede agregar sus propias skills en `.review-skills/`, que se leen de la rama base para que un PR no pueda debilitar su propia revisión.
- Proveedor de modelos configurable: Azure OpenAI con el deployment `gpt-4.1-mini` por defecto (autenticación con API key) o Claude de Anthropic. Los tres agentes usan el mismo proveedor; el deployment o modelo se puede cambiar por agente.
- Despliegue: el revisor se distribuye como imagen Docker versionada en GitHub Container Registry (GHCR) y la GitHub Action ejecuta la imagen de su misma versión. Este repo tiene su propio pipeline (lint, tests, build, escaneo de vulnerabilidades y publicación), releases con semver y una guía de despliegue para los repos objetivo.

## Capabilities

### New Capabilities
- `review-orchestration`: recolección del contexto del PR, ejecución paralela de los subagentes, proveedor de modelos configurable, consolidación de hallazgos, veredicto y publicación en GitHub.
- `functional-review`: resolución de la tarea referenciada por hashtag y validación del cambio contra la tarea y las especificaciones.
- `security-review`: detección de problemas de seguridad complementarios a Sonar.
- `design-review`: verificación de arquitectura, patrones y estándares definidos para el repo objetivo.
- `ci-integration`: GitHub Action para invocar el revisor desde el pipeline del repo objetivo, con permisos, secretos y modos de fallo definidos. La Action ejecuta la imagen publicada.
- `review-skills`: formato, selección por archivos cambiados, skills incluidas y skills propias del repo objetivo leídas de la rama base.
- `agent-distribution`: empaquetado del revisor como imagen Docker, pipeline de publicación con controles de calidad, versionado, ejecución local y rollback.

### Modified Capabilities
<!-- Ninguna: el proyecto no tiene especificaciones previas. -->

## Impact

- **Código nuevo** en este repo: paquete `reviewer/` (contexto, agentes, orquestador, publicador, CLI), `action.yml`, `Dockerfile`, workflows `ci.yml` y `release.yml`, tests con pytest, README y `docs/DEPLOYMENT.md`. Ya existe un borrador parcial sin commitear (`pyproject.toml`, `reviewer/models.py`, `diff.py`, `github.py`, `sonar.py`, `context.py`) que la implementación debe ajustar a estas especificaciones.
- **Dependencias**: `langgraph` (orquestación), `openai` (Azure OpenAI), `anthropic`, `httpx`, `pydantic`, `pyyaml`. Python ≥ 3.10.
- **Plataforma de despliegue**: GitHub Actions (runners de GitHub, sin servidores propios) y GitHub Container Registry. El paquete de la imagen hay que hacerlo público a mano, una vez, para que otros repos puedan descargarlo.
- **Servicios externos**: Azure OpenAI (secrets `AZURE_OPENAI_API_KEY` y `AZURE_OPENAI_ENDPOINT`, y un deployment de `gpt-4.1-mini` en el recurso) o, como alternativa, la API de Claude (`ANTHROPIC_API_KEY`); API REST de GitHub (`GITHUB_TOKEN` con `pull-requests: write`) y, opcionalmente, la API de SonarCloud (`SONAR_TOKEN`).
- **Repos objetivo**: necesitan un job nuevo en su workflow, los secrets del proveedor de modelos, una carpeta de tareas `.md` y la convención del hashtag en la descripción de los PRs. Que `REVIEW_GUIDELINES.md` tenga contenido es recomendable, pero no obligatorio.
- **Costo**: cada PR genera tres llamadas al proveedor de modelos. El costo crece con el tamaño del diff; `gpt-4.1-mini` es varias veces más barato que Claude Opus, a cambio de una revisión menos profunda.
