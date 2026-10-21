# Design

## Context

- Este repositorio (`LizaCerinza/Code-review-miltiagent`) solo contiene el revisor. El código a revisar vive en otros repos; el primero es `farsov/Code-review-miltiagent`, un backend NestJS con arquitectura hexagonal, Vitest y un CI con lint, typecheck, tests y Sonar con Quality Gate.
- En ese repo objetivo, ESLint (incluido `eslint-plugin-boundaries`) ya controla el formato y qué capas pueden importar a cuáles, y Sonar ya cubre las reglas estáticas. Los agentes tienen que aportar lo que esas herramientas no detectan.
- `REVIEW_GUIDELINES.md` existe en el repo objetivo, pero hoy está vacío. Las especificaciones viven en `openspec/specs/`.
- Ya hay un borrador sin commitear de `reviewer/` (modelos, diff, cliente de GitHub, Sonar y contexto). Se reutiliza y se ajusta a las specs; no es una base cerrada.
- Entorno local: Python 3.10 (Windows). En CI se usa 3.12. El código debe funcionar en ambas versiones.

## Goals / Non-Goals

**Goals:**
- Una sola herramienta que funcione igual en local (modo dry-run) y en CI.
- Orquestación determinista: el código decide qué corre, cuándo y con qué contexto, y el modelo solo produce hallazgos.
- Resultados reproducibles y testeables sin llamar a la API.
- Costo acotado: tres llamadas por ejecución, sin bucles abiertos.

**Non-Goals:**
- Aplicar correcciones automáticas o hacer commits al PR.
- Exploración libre del repositorio por parte de los agentes (uso de herramientas). Queda para una fase posterior.
- Soportar otros stacks además de NestJS en esta versión. Los prompts están pensados para NestJS, pero las guías del repo objetivo pueden ampliarlos.
- Otros proveedores de CI (GitLab, Azure DevOps).

## Decisions

### 1. Repositorio Python aparte, distribuido como imagen Docker y ejecutado por una Action compuesta
El revisor es un paquete Python con su CLI (`python -m reviewer`), empaquetado en una imagen publicada en `ghcr.io/lizacerinza/code-review-miltiagent` (GHCR exige el nombre en minúsculas). `action.yml` es una Action compuesta que hace `docker run` de esa imagen. Las entradas se pasan como variables de entorno y `GITHUB_WORKSPACE` se monta en `/workspace`.
- *Qué imagen usa la Action*: la deduce de `github.action_ref`. `vX`, `vX.Y` y `vX.Y.Z` se convierten en `X`, `X.Y` y `X.Y.Z`; `main` se convierte en `edge`. Con cualquier otra referencia (rama o SHA), la Action falla y pide la entrada `image`. La entrada `image` siempre tiene prioridad.
- *Alternativas*: (a) un módulo TypeScript dentro de cada repo objetivo, que acopla el revisor al proyecto revisado; (b) una Action compuesta que haga `pip install` en cada ejecución: más lenta y con dependencias resueltas en cada corrida, así que no es reproducible; (c) una Action `using: docker` con `Dockerfile`, que se reconstruye en cada ejecución; (d) una Action `using: docker` con la imagen fija en `action.yml`, que obliga a editar ese archivo en cada release; (e) publicar el paquete en PyPI, que no aísla el runtime.
- *Por qué*: lo que se probó es exactamente lo que corre (la misma imagen por digest), arranca rápido, el rollback es solo cambiar la referencia y la misma imagen sirve en local o en otro CI.

### 2. Orquestación con un grafo de LangGraph de fan-out/fan-in fijo
El contexto se construye una sola vez, fuera del grafo. El grafo (`StateGraph`) tiene un nodo por agente, conectados desde `START` en paralelo, y un nodo `aggregate` que recibe una arista de cada uno, así que se ejecuta cuando terminan los tres. El estado guarda el contexto, la lista `reports` (con el reducer `operator.add`, para que cada agente agregue su reporte sin pisar los demás) y el `result`. Cada nodo de agente envuelve la ejecución con un timeout y convierte cualquier fallo en un `AgentReport` con error, de modo que el grafo nunca falla por un agente. `aggregate` descarta los hallazgos sin evidencia, consolida duplicados, agrega los hallazgos de tarea ausente y aplica la política de veredicto.
- *Por qué LangGraph*: es el marco de la materia. Hace explícita y dibujable la arquitectura multiagente (`get_graph().draw_mermaid()` sirve para la documentación de la tesis), integra trazas con LangSmith si se define `LANGSMITH_TRACING`, y deja preparado el camino para extensiones como un nodo "juez" que verifique los críticos o reintentos condicionales.
- *Qué no se usa*: ni supervisor LLM ni aristas condicionales. El flujo sigue siendo determinista (siempre los tres agentes), así que el veredicto se puede testear sin llamar al modelo.
- *Alternativas*: (a) `asyncio.gather` sin framework (la primera versión), con menos dependencias pero sin grafo explícito ni trazas; (b) un supervisor LLM que decida a qué agente llamar, que agrega no determinismo y costo sin beneficio; (c) un único prompt con los tres roles, que pierde especialización.

### 3. Proveedor de modelos detrás de una interfaz, con Azure OpenAI por defecto
Los agentes no dependen de un SDK concreto: llaman a `LLMProvider.complete_json(system, user, schema, model)`, que devuelve el texto JSON y el uso de tokens. Hay dos implementaciones, y la elección se hace con `provider` (por defecto `azure`):
- **Azure OpenAI** (`provider=azure`): SDK oficial `openai` con `AsyncAzureOpenAI`, autenticación con API key (`AZURE_OPENAI_API_KEY`), endpoint del recurso (`AZURE_OPENAI_ENDPOINT`) y versión de la API (por defecto `2024-10-21`, la GA con salidas estructuradas). El "modelo" es el nombre del **deployment** (por defecto `gpt-4.1-mini`). Usa `response_format` con `json_schema` estricto y `temperature` 0.1 para estabilizar la salida. `finish_reason` `length` o `content_filter` y los `refusal` del mensaje se tratan como error del agente.
- **Anthropic** (`provider=anthropic`): la llamada original con `claude-opus-5-5` por defecto, streaming, `output_config.format`, `effort` configurable y `fallbacks: "default"`.
- En los dos casos el esquema es el mismo (JSON Schema estricto con `additionalProperties: false`) y la respuesta se valida con pydantic.
- *Por qué una interfaz propia y no los chat models de LangChain*: los wrappers de LangChain para salida estructurada con Claude fuerzan `tool_choice`, que `claude-opus-5-5` rechaza, y esconden parámetros que se usan (`effort`, `fallbacks`, `json_schema` estricto). Con los SDK nativos cada proveedor usa su mecanismo de salida estructurada garantizada, y LangGraph sigue orquestando sin depender de eso.
- *Modelo por agente*: `REVIEWER_MODEL_<AGENTE>` permite, por ejemplo, usar un deployment más capaz solo para seguridad.
- *Alternativas*: (a) solo Azure, con menos código pero sin poder comparar modelos; (b) agentes con herramientas (tool use) para explorar el repo, con costo variable y mayor superficie de ataque; (c) parsear JSON libre del texto, que es frágil.

### 4. Contexto de una sola pasada, con presupuesto explícito
El contexto incluye: metadatos del PR, diff por archivo, contenido completo de los archivos cambiados (leído del checkout), un índice de rutas del repo (para que el agente de diseño pueda señalar que algo ya existe) y los documentos de cada agente: la tarea y los specs al funcional, los issues de Sonar al de seguridad y las guías al de diseño. Se excluyen lockfiles, `dist/`, `coverage/` y binarios. Si se supera el presupuesto, se omiten archivos completos y se informa (nunca se trunca a la mitad).
- Los datos que vienen del PR van dentro de etiquetas (`<diff>`, `<archivos>`, `<tarea>`, ...) y el prompt de sistema los declara como datos no confiables.
- El checkout en CI se hace sobre `pull_request.head.sha`, para que los números de línea coincidan con el diff de la API de GitHub.

### 5. La tarea se resuelve en código, no en el modelo
Una expresión regular extrae los hashtags `#<nombre>` no numéricos del título y la descripción, les quita un `.md` final y los busca en `<tasks-dir>/<nombre>.md`. Si falta la tarea, el hallazgo `critical` lo genera el orquestador directamente (con evidencia: el texto de la descripción), sin gastar una llamada. El agente funcional se ejecuta igual, solo contra los specs, para detectar regresiones.
- *Alternativa*: dejar que el modelo encuentre la tarea en la descripción. Es menos predecible y no permite garantizar el bloqueo.
- Para evitar path traversal, el nombre se valida con `[A-Za-z0-9._-]+` y la ruta resuelta debe quedar dentro de `tasks-dir`.

### 6. Modelo de hallazgo, confianza y veredicto
`Finding` = archivo, línea, severidad, confianza, categoría, título, mensaje, evidencia, sugerencia y agentes. La huella (`sha1(archivo:línea:título_normalizado)`) sirve para consolidar duplicados y evitar comentarios repetidos. El veredicto es bloqueante si existe un hallazgo con `severity.rank <= fail_on.rank` y `confidence == high`. `fail_on` acepta además `none` (solo comenta, nunca bloquea), útil durante la adopción.
- *Por qué confianza*: los PRs escritos por IA generan muchos casos ambiguos. Separar "grave" de "seguro" reduce los falsos bloqueos sin esconder los hallazgos.

### 7. Publicación idempotente en GitHub
- Resumen: un comentario de issue con el marcador `<!-- ai-review:summary -->`, que se edita si ya existe.
- Inline: una review con `event: COMMENT` y solo los hallazgos cuya línea está entre las líneas comentables del patch (agregadas o de contexto, lado RIGHT). Cada comentario lleva `<!-- ai-review:fp=<huella> -->` y se omiten las huellas ya publicadas. Si GitHub responde 422, se publica solo el resumen y se registra una advertencia.
- Solo el publicador escribe en GitHub. Los agentes no tienen herramientas ni credenciales de GitHub.

### 8. Sonar como fuente de deduplicación, no como requisito
Se consulta `GET /api/issues/search?componentKeys=<key>&pullRequest=<n>&resolved=false`. La clave del proyecto se lee de `sonar-project.properties` del repo objetivo. Ante cualquier error se continúa con una lista vacía y se avisa en el resumen. En el workflow, el job de revisión va con `needs:` después del job que ejecuta Sonar, para que los issues ya existan.

### 9. Estructura del paquete
```text
reviewer/
  __main__.py      CLI (modos PR y local), códigos de salida, reporte JSON y step summary
  config.py        opciones (CLI y variables de entorno) y valores por defecto
  models.py        Severity, Confidence, Finding, AgentReport, ReviewResult
  diff.py          parseo de diffs y líneas comentables
  context.py       ReviewContext y su construcción (exclusiones, presupuesto, índice del repo)
  tasks.py         resolución de tareas por hashtag
  github.py        cliente REST (lectura del PR, resumen, review)
  sonar.py         issues del PR
  llm/             LLMProvider + azure.py (AsyncAzureOpenAI) + anthropic.py, y create_provider()
  agents/          base.py (esquema, prompt común, parseo) + functional.py, security.py, design.py
  orchestrator.py  grafo de LangGraph: nodos de agente con timeout y nodo aggregate
  aggregator.py    filtro de evidencia, consolidación y veredicto
  report.py        Markdown del resumen y de los comentarios inline
  publisher.py     publicación idempotente
action.yml           Action compuesta: resuelve la imagen y hace docker run
Dockerfile           imagen multi-stage, usuario sin root
.dockerignore
.github/workflows/
  ci.yml             PRs y main: ruff, pytest, docker build; en main publica edge
  release.yml        tags vX.Y.Z: tests, build, Trivy, push a GHCR, tag mayor y release
docs/DEPLOYMENT.md   guía de despliegue en un repo objetivo
examples/            job de ejemplo y plantilla de tarea
```

### 10. Estrategia de pruebas
Las pruebas unitarias con pytest no llaman a la API: el parseo de diffs, la resolución de tareas, el agregador y el veredicto, el render del Markdown, el parseo de respuestas con objetos falsos y el orquestador con agentes falsos (incluido uno que falla y otro que excede el timeout). El cliente de GitHub se prueba con `httpx.MockTransport`. Por separado, un conjunto de PRs de ejemplo con defectos conocidos (en el repo NestJS) sirve para la evaluación manual de la tesis.

### 11. Imagen Docker
Imagen multi-stage sobre `python:3.12-slim`. La primera etapa construye el wheel del paquete; la final lo instala sin compiladores ni caché de pip, crea un usuario sin privilegios y define `ENTRYPOINT ["python", "-m", "reviewer"]` y `WORKDIR /workspace`. No se copian `.env`, tests, `.git` ni `openspec/` (`.dockerignore`). Lleva las etiquetas OCI (`org.opencontainers.image.source`, `version` y `revision`) para que GHCR asocie el paquete al repo.
- *Detalle del montaje*: el runner monta el workspace con otro UID, así que la imagen solo necesita leerlo. Los reportes (JSON) se escriben en un directorio indicado por la variable `REVIEWER_OUTPUT_DIR`, que la Action monta con permisos de escritura.
- *Alternativa*: `python:3.12-alpine`, que es más chica pero da problemas con wheels nativos (por ejemplo, de las dependencias de `httpx` y `pydantic-core`).

### 12. Pipeline de publicación
- `ci.yml` (en `pull_request` y `push` a `main`): `ruff check`, `pytest` y `docker build`. En `main` también publica `edge` en GHCR con `docker/build-push-action`.
- `release.yml` (en tags `v*.*.*`): repite lint y tests, construye la imagen, la escanea con Trivy (falla con severidad `CRITICAL` y `ignore-unfixed`), la publica con los tags `X.Y.Z`, `X.Y` y `X` mediante `docker/metadata-action`, mueve el tag de git `vX` y crea el GitHub Release con notas generadas automáticamente.
- Permisos: `packages: write` y `contents: write` solo en el job de publicación. La autenticación con GHCR usa `GITHUB_TOKEN`, sin secrets adicionales.
- *Alternativas*: (a) Docker Hub, que obliga a manejar otra cuenta y otro token; (b) release-please para automatizar las versiones, que agrega convenciones extra innecesarias para el tamaño del proyecto. Se puede sumar más adelante.

### 13. Skills como archivos que selecciona el orquestador
El conocimiento de cada agente vive en `reviewer/skills/library/<agente>/<skill>/SKILL.md` (encabezado YAML con `name`, `agent`, `description` y `applies_to`). El prompt de sistema de cada agente queda como: rol breve + skills seleccionadas + reglas comunes (datos no confiables, formato de hallazgos). Las reglas comunes no son una skill, para que nunca se puedan omitir ni reemplazar.
- *Selección*: en código, por patrones glob (`fnmatch`) sobre las rutas cambiadas del PR (después de las exclusiones). Una skill sin `applies_to` aplica siempre.
- *Skills del repo objetivo*: carpeta `.review-skills/` (configurable con `skills-dir`), leída de la **rama base**. En modo PR se usa la API de GitHub (`git/trees/<base_sha>?recursive=1` y `contents/<ruta>?ref=<base_sha>`), porque el checkout del job tiene el head del PR y no siempre el historial de la base. En modo local se usa `git ls-tree` / `git show` sobre la rama base. Si el PR toca la carpeta, se agrega una nota al resumen.
- *Empaquetado*: las skills incluidas son `package-data` del paquete Python, así que viajan dentro de la imagen Docker. `pyyaml` pasa a ser dependencia de ejecución.
- *Alternativas*: (a) Agent Skills nativas de Claude, que el modelo carga por su cuenta mediante herramientas: no existen en Azure OpenAI y convierten cada agente en un bucle agéntico de costo variable; (b) prompts monolíticos dentro del código (la versión anterior): más largos, mezclan temas que el PR no toca y no se pueden ampliar por repo; (c) leer las skills del repo desde el checkout del PR: más simple, pero el PR podría debilitar su propia revisión.
- *Por qué*: prompts más cortos y enfocados (importante con un modelo chico como `gpt-4.1-mini`), conocimiento editable sin tocar Python, reglas propias por repo y la posibilidad de medir qué skill aporta hallazgos.

### 14. Ajustes tras la primera prueba real (gpt-4.1-mini)
Se ejecutó el revisor en local sobre una rama del repo NestJS con 8 errores sembrados (tarea `#buscar-usuarios`). Resultado: detectó 4 claramente (inyección SQL, falta de 400, falta de límite de 20, falta del caso de uso) y 1 parcialmente (controller que usa el repositorio, como `minor`). No detectó la afirmación falsa del commit ("incluye tests"), y el resumen del agente funcional incluso la repitió. Además, el mismo problema apareció hasta 3 veces, reportado por agentes distintos con títulos distintos. Costo: unos 20 000 tokens de entrada y 2 000 de salida.

Ajustes:
- *Duplicados entre agentes*: además de la huella exacta, se unen hallazgos de agentes **distintos** en el mismo archivo, a ≤ 3 líneas, con títulos similares (coeficiente de solapamiento ≥ 0,5 sobre raíces de 5 letras, sin acentos ni palabras vacías). Calibrado con los hallazgos reales: los duplicados dieron 0,60–0,75 y los problemas distintos ≤ 0,34. Los hallazgos del mismo agente nunca se unen por similitud. Resultado sobre la prueba: 9 → 5 hallazgos.
- *Especialización*: cada rol dice explícitamente qué no le toca reportar, y una regla común lo refuerza.
- *Afirmaciones*: la skill `scope-and-claims` exige listar cada afirmación de la descripción y buscar su evidencia en el diff. Una regla común prohíbe que el `summary` contradiga los hallazgos o repita afirmaciones no verificadas.
- *Capas*: la skill `hexagonal-layers` nombra explícitamente el controller que inyecta un repositorio (`major`) y la lógica de negocio (filtrado, orden, límites, normalización) en el controller.
- *No se agrega* una detección determinista de "PR sin tests": la cobertura ya la exige el pipeline del repo objetivo antes de la revisión (`test:cov` con umbral del 80 % y el Quality Gate de Sonar). El agente funcional sigue señalando los criterios de la tarea sin un test específico (`missing-test`, `minor`).
- *Alternativa descartada para los duplicados*: unir solo por archivo y línea cercana, que habría mezclado los tres problemas distintos que el agente funcional reportó en la misma línea.

**Segunda prueba (mismos errores sembrados, con los ajustes):** detectó 6 de 8 (se sumaron el controller que usa el repositorio como `major` y la falta de tests), y la validación de `q` dejó de duplicarse. Persistieron dos fallas:
- *Afirmaciones falsas*: ningún hallazgo `unsupported-claim`, y el resumen del agente funcional todavía repetía la descripción antes de contradecirla. Es una limitación del modelo: `gpt-4.1-mini` no ejecuta el procedimiento de la skill.
- *Inyección SQL duplicada*: seguridad (critical) y diseño+funcional (major) usaron títulos sin palabras en común, pero citaron exactamente el mismo código.

Ajustes:
- *Duplicados por evidencia*: también se unen hallazgos de agentes distintos, en el mismo archivo y a ≤ 3 líneas, si las líneas de código citadas coinciden (Jaccard ≥ 0,85). El umbral es alto a propósito: dos problemas distintos que citaban el mismo método dieron 0,71. Sobre la segunda prueba: 8 → 7 hallazgos, solo se une la inyección SQL.
- *Modelos de razonamiento en Azure*: un deployment cuyo nombre empieza con `gpt-5`, `o1`, `o3` u `o4` (o que se declara en `REVIEWER_AZURE_REASONING_MODELS`) se invoca sin `temperature`, con `max_completion_tokens`, con `reasoning_effort` (por defecto `medium`) y con la versión de la API `2025-04-01-preview`, porque la versión GA `2024-10-21` no los soporta. Los demás deployments siguen igual.
- *Modelo por agente en la Action*: entradas `model-functional`, `model-security` y `model-design`. Combinación recomendada por costo/beneficio: `gpt-5-mini` para el agente funcional (verificar afirmaciones exige razonar) y `gpt-4.1-mini` para seguridad y diseño, que ya rinden bien. Costo estimado: 1 a 2 centavos de dólar por PR.

## Risks / Trade-offs

- [Falsos positivos que frenan PRs] → Solo bloquea `critical` con confianza `high`, el umbral es configurable y existe `fail_on: none` para empezar en modo solo-comentarios.
- [Prompt injection desde el PR, más probable en código generado por IA] → Datos dentro de etiquetas, reglas explícitas en el prompt de sistema, agentes sin herramientas y salida restringida por esquema. Los intentos se reportan como `critical`.
- [Diffs grandes que superan el presupuesto] → Se omiten archivos completos, se avisa en el resumen y el diff siempre se incluye. Más adelante se podría paginar por módulos.
- [Respuestas no deterministas entre ejecuciones] → Consolidación por huella y comentarios inline idempotentes. El veredicto depende solo de hallazgos con evidencia citada.
- [`gpt-4.1-mini` es un modelo chico y sin razonamiento: detecta menos problemas sutiles (IDOR, carreras, alcance)] → Deployment configurable por agente (por ejemplo, uno más capaz solo para seguridad), proveedor `anthropic` como alternativa y modo `fail-on: none` mientras se evalúa la calidad.
- [El filtro de contenido de Azure puede bloquear prompts o respuestas sobre vulnerabilidades] → `content_filter` se reporta como error del agente con el motivo (la revisión queda "incompleta", no aprobada en silencio); si ocurre seguido, se ajusta la política de filtros del deployment.
- [Una skill del repo objetivo mal escrita o demasiado larga degrada la revisión] → Las skills del repo pasan por revisión de código como cualquier cambio, se leen de la rama base y el resumen lista cuáles usó cada agente; las inválidas se ignoran con aviso.
- [Las guías (`REVIEW_GUIDELINES.md`) y las specs todavía se leen del checkout del PR, así que un PR podría editarlas a su favor] → Por ahora se acepta (las tareas y specs nuevas suelen llegar en el mismo PR); los agentes ven esos cambios en el diff. Leer las guías de la base es una mejora futura.
- [Costo por PR] → Modelo configurable por agente y presupuesto de contexto acotado. El uso de tokens de cada ejecución se muestra en el reporte JSON.
- [El agente de diseño no ve todo el repo y no siempre detecta duplicación] → El índice de rutas y los archivos cambiados mitigan parte del problema. La exploración con herramientas queda fuera de alcance (Non-Goals).
- [Colisión de hashtags con otros usos] → Solo se consideran hashtags no numéricos que resuelven a un archivo existente. Un hashtag que no resuelve se reporta, para que se note.
- [PRs desde forks sin secretos] → La revisión se omite con un aviso, de acuerdo con la spec de `ci-integration`.
- [El paquete de GHCR nace privado y el repo objetivo no puede descargarlo] → La guía incluye el paso manual de hacerlo público. Si `docker pull` falla, la Action muestra un error que apunta a ese paso.
- [Referencia de la Action sin imagen correspondiente (rama o SHA)] → La Action falla con un mensaje que pide la entrada `image`, en lugar de usar una imagen equivocada.
- [Docker no está instalado en la máquina local] → La imagen se verifica en CI. En local se puede usar la CLI con `pip install -e .`.
- [Dependencias con vulnerabilidades nuevas después de publicar] → Trivy corre en cada release. Una versión de parche con la imagen base actualizada se publica con un tag nuevo, sin sobrescribir los anteriores.

## Migration Plan

1. Implementar el revisor y probarlo en local con la CLI en modo local contra ramas del repo NestJS.
2. Integrar en `main` (se publica `edge`) y crear el tag `v0.1.0`, que publica las imágenes `0.1.0`, `0.1` y `0`, el tag `v0` y el release.
3. Hacer público el paquete en GHCR (paso manual, una sola vez).
4. En el repo NestJS: crear `docs/tasks/`, agregar el secret `ANTHROPIC_API_KEY` y el job `ai-review` con `uses: LizaCerinza/Code-review-miltiagent@v0`, `needs: quality` y `fail-on: none`.
5. Abrir PRs de prueba con defectos conocidos y ajustar los prompts, publicando versiones de parche.
6. Publicar `v1.0.0`, pasar a `fail-on: critical` y agregar el check a la protección de rama.
- **Rollback**: fijar una versión anterior (`@v0.1.0`), volver a `fail-on: none` o quitar el job. Las imágenes publicadas nunca se sobrescriben y el revisor no modifica el código del repo objetivo.

## Open Questions

- Formato definitivo de los archivos de tarea (secciones obligatorias como "Criterios de aceptación"). El agente funciona con Markdown libre, pero una plantilla mejoraría la precisión.
