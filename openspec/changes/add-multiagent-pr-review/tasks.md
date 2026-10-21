# Tasks

## 1. Base del proyecto

- [x] 1.1 Ajustar `pyproject.toml` (dependencias `anthropic`, `httpx`, `pydantic`; extras `dev` con pytest, pytest-asyncio y ruff; script `code-review-agent`) y verificar que `pip install -e .[dev]` termina sin errores en Python 3.10
- [x] 1.2 Crear `reviewer/config.py` con las opciones y sus valores por defecto (modelo, effort, timeout por agente, `fail_on` incluido `none`, `fail_on_agent_error`, `tasks_dir`, `spec_globs`, `guidelines_file`, límites de tamaño), leídas desde la CLI y las variables de entorno, y verificar con `tests/test_config.py` que los valores por defecto coinciden con la spec de `ci-integration`

## 2. Modelos, diff y contexto

- [x] 2.1 Completar `reviewer/models.py` con `Confidence`, el campo `confidence` en `Finding`, el estado de cada agente (`ok` | `error`) y el uso de tokens en `AgentReport`, y verificar con `tests/test_models.py` el orden de severidades y la huella estable
- [x] 2.2 Revisar `reviewer/diff.py` (líneas comentables y división de `git diff`) y verificar con `tests/test_diff.py` los casos de hunks múltiples, archivo nuevo, archivo eliminado y "\ No newline at end of file"
- [x] 2.3 Completar `reviewer/context.py`: exclusiones, presupuesto con omisión explícita, índice de rutas del repo y bloques de datos dentro de etiquetas. Verificar con `tests/test_context.py` que se excluye `package-lock.json`, que un archivo grande aparece en `omitted` y que los archivos eliminados no aportan contenido
- [x] 2.4 Crear `reviewer/tasks.py` (extracción de hashtags no numéricos, `.md` opcional, validación del nombre, ruta confinada a `tasks_dir`) y verificar con `tests/test_tasks.py` los escenarios de la spec `functional-review` (hashtag válido, con extensión, `#12` ignorado, varias tareas, inexistente, intento `#../secret`)

## 3. Agentes

- [x] 3.1 Completar `reviewer/agents/base.py`: esquema JSON con `confidence`, reglas comunes contra prompt injection, llamada con streaming, `effort`, `fallbacks: "default"` y modelo por agente, y `parse_report`. Verificar con `tests/test_agent_base.py`, usando respuestas falsas, el caso válido, `refusal`, `max_tokens` y JSON inválido
- [x] 3.2 Implementar `reviewer/agents/functional.py` (prompt con criterios cumple / no cumple / no verificable, alcance, afirmaciones de la descripción, cobertura de tests y regresiones contra specs; entrada: tarea(s), specs y PR) y verificar con un test que `build_input` incluye las etiquetas `<tarea>` y `<especificaciones>`
- [x] 3.3 Implementar `reviewer/agents/security.py` (prompt con las categorías de la spec `security-review`, regla de no duplicar Sonar y severidad según explotabilidad; entrada: PR e issues de Sonar) y verificar con un test que `build_input` incluye `<sonar>` y el aviso cuando Sonar no está disponible
- [x] 3.4 Implementar `reviewer/agents/design.py` (prompt con capas hexagonales, patrones existentes, duplicación, SOLID, contratos y pruebas, sin duplicar el linter; entrada: guías, índice del repo y PR) y verificar con un test el aviso de "sin guías definidas" cuando el archivo está vacío

## 4. Orquestación y veredicto

- [x] 4.1 Implementar `reviewer/orchestrator.py` (ejecución paralela con timeout por agente y conversión de excepciones en `AgentReport` con error) y verificar con `tests/test_orchestrator.py`, usando agentes falsos, que un agente que falla y otro que excede el timeout no impiden los resultados de los demás
- [x] 4.2 Implementar `reviewer/aggregator.py` (descarte sin evidencia, consolidación por huella con la severidad máxima y los agentes unidos, veredicto con `fail_on` y confianza `high`, estado "incompleta") y verificar con `tests/test_aggregator.py` cada escenario de veredicto de la spec `review-orchestration`
- [x] 4.3 Hacer que el orquestador genere el hallazgo `critical` de tarea ausente o inexistente sin llamar al modelo, y verificarlo con un test

## 5. Reporte y publicación

- [x] 5.1 Implementar `reviewer/report.py` (Markdown del resumen con veredicto, estado por agente, conteos, archivos omitidos, Sonar no disponible y "requiere verificación humana"; cuerpo inline con marcador de huella) y verificar con `tests/test_report.py`
- [x] 5.2 Completar `reviewer/github.py` y crear `reviewer/publisher.py` (actualizar el resumen en vez de duplicarlo, inline solo en líneas comentables, saltar huellas existentes y, ante un 422, publicar solo el resumen) y verificar con `tests/test_publisher.py` usando `httpx.MockTransport` que una segunda ejecución edita el resumen y no repite comentarios
- [x] 5.3 Revisar `reviewer/sonar.py` (lectura de `sonar.projectKey`, issues del PR y lista vacía con aviso ante error) y verificar con un test con `MockTransport`

## 6. CLI y GitHub Action

- [x] 6.1 Implementar `reviewer/__main__.py` con los modos PR y local (`--local --base main`, sin escrituras en GitHub), el reporte JSON en `REVIEWER_OUTPUT_DIR` (por defecto, el directorio actual), el step summary cuando existe `GITHUB_STEP_SUMMARY` y los códigos de salida 0/1/2. Verificar con `tests/test_cli.py` (credencial ausente → 2 sin llamar a agentes; bloqueante → 1) y ejecutando a mano `python -m reviewer --local --base main --workspace ../Code-review-miltiagent`
- [x] 6.2 Crear `action.yml` compuesto: entradas con valores por defecto, incluida `image`; la imagen se resuelve desde `github.action_ref` (`vX[.Y[.Z]]` → `X[.Y[.Z]]`, `main` → `edge`, otra referencia → error que pide `image`); se omite fuera de `pull_request` o sin credencial; hace `docker run` montando `GITHUB_WORKSPACE`, el directorio de salida y `GITHUB_STEP_SUMMARY`, con las variables pasadas por `env` y no interpoladas en `run`; y da un mensaje claro si `docker pull` falla. Verificar que el YAML es válido, que las entradas coinciden con la spec `ci-integration` y que la resolución de la imagen tiene un test (extraída a un script de shell probado en `ci.yml`)
- [x] 6.3 Escribir `examples/ai-review-job.yml` para el repo objetivo (`uses: LizaCerinza/Code-review-miltiagent@v0`, `needs: quality`, permisos mínimos, checkout de `head.sha`, subida del reporte JSON como artefacto) y `examples/task-template.md` con la convención del hashtag

## 7. Distribución y despliegue

- [ ] 7.1 Crear el `Dockerfile` multi-stage (`python:3.12-slim`, wheel en la primera etapa, usuario sin root, `ENTRYPOINT ["python", "-m", "reviewer"]`, `WORKDIR /workspace`, etiquetas OCI) y el `.dockerignore` (excluir `.git`, `.env`, `tests/`, `openspec/`, cachés). Verificar en CI que `docker build` funciona, que `docker run <imagen> --help` termina con 0 y que `docker run <imagen> id -u` no devuelve 0
- [ ] 7.2 Crear `.github/workflows/ci.yml` (en `pull_request` y `push` a `main`: `ruff check`, `pytest`, `docker build`, prueba del script de resolución de imagen; en `main`, publicar `edge` en GHCR con `packages: write` solo en ese job) y verificar con un PR de prueba que corre sin publicar y que un merge a `main` publica `ghcr.io/lizacerinza/code-review-miltiagent:edge`
- [ ] 7.3 Crear `.github/workflows/release.yml` (en tags `v*.*.*`: lint, tests, build, escaneo con Trivy que falla con `CRITICAL` corregible, push con los tags `X.Y.Z`, `X.Y` y `X` vía `docker/metadata-action`, actualización del tag de git `vX` y GitHub Release con notas generadas) y verificar con el tag `v0.1.0` que existen las tres imágenes con el mismo digest, el tag `v0` y el release
- [ ] 7.4 Escribir `docs/DEPLOYMENT.md`: requisitos, hacer público el paquete en GHCR, secrets del repo objetivo (`ANTHROPIC_API_KEY` y, opcionalmente, `SONAR_TOKEN`), job de ejemplo, carpeta `docs/tasks/`, adopción gradual con `fail-on: none` → `critical`, protección de rama, rotación de la API key, uso local con `docker run`, rollback fijando una versión y solución de problemas (`docker pull` denegado, PRs de forks, permisos). Verificar siguiendo la guía en el repo NestJS (tarea 8.3)

## 8. Documentación e integración

- [x] 8.1 Escribir `README.md` (qué hace cada agente, convención `#<tarea>`, instalación, uso local con la CLI y con Docker, uso en CI, entradas, códigos de salida, versionado y costos, con un enlace a `docs/DEPLOYMENT.md`) y verificar que los comandos documentados que no requieren Docker se ejecutan tal como están escritos
- [x] 8.2 Ejecutar `ruff check .` y `pytest` y verificar que pasan sin errores
- [ ] 8.3 Prueba de integración real siguiendo `docs/DEPLOYMENT.md`: en un fork o rama del repo NestJS, abrir un PR con defectos conocidos (requisito incumplido, IDOR y lógica en el controller) usando `@v0` con `fail-on: none`, y verificar que el resumen y los comentarios inline aparecen una sola vez después de dos pushes y que el reporte JSON queda como artefacto

## 9. Proveedores de modelos y LangGraph

- [x] 9.1 Crear `reviewer/llm/` con la interfaz `LLMProvider` (`complete_json`), el proveedor `anthropic` (la llamada actual con streaming, `effort` y `fallbacks`) y `create_provider(config, env)`. Hacer que `Agent.run` use el proveedor y que `parse_report` reciba el texto JSON. Verificar con `tests/test_llm.py` y los tests de agentes actualizados (proveedor falso que registra la petición)
- [x] 9.2 Implementar el proveedor `azure` (`AsyncAzureOpenAI`, deployment como modelo, `response_format` `json_schema` estricto, `temperature` 0.1, errores por `length`, `content_filter` y `refusal`) y verificar con `tests/test_llm.py` usando `httpx.MockTransport` la petición enviada (ruta del deployment, `api-version`, `api-key`) y cada caso de error
- [x] 9.3 Agregar a `config.py` `provider` (`azure` por defecto), el modelo por defecto según el proveedor (`gpt-4.1-mini` / `claude-opus-5-5`) y `azure_api_version`, y hacer que la CLI exija las credenciales del proveedor elegido (`AZURE_OPENAI_API_KEY` y `AZURE_OPENAI_ENDPOINT`, o las de Anthropic). Verificar con `tests/test_config.py` y `tests/test_cli.py`
- [x] 9.4 Reescribir `reviewer/orchestrator.py` como un grafo de LangGraph (nodos de agente en paralelo desde `START`, reducer `operator.add` en `reports`, nodo `aggregate`) que conserve el timeout por agente y la conversión de errores, y exponer el diagrama Mermaid del grafo. Verificar que `tests/test_orchestrator.py` sigue pasando y agregar un test de la estructura del grafo
- [x] 9.5 Actualizar `action.yml` (entradas `provider`, `azure-openai-api-key`, `azure-openai-endpoint`, `azure-openai-api-version`; omisión por falta de credencial según el proveedor) y verificar con `tests/test_action.py`
- [x] 9.6 Actualizar `README.md`, `docs/DEPLOYMENT.md` (crear el recurso y el deployment en Azure, secrets, rotación de la key) y `examples/ai-review-job.yml`, incluir el diagrama del grafo, y verificar que `ruff check .` y `pytest` pasan

## 10. Skills de revisión

- [x] 10.1 Crear `reviewer/skills/` (modelo `Skill`, parseo del encabezado YAML con validación, carga de las skills incluidas como `package-data`, combinación con las del repo por `name` y selección por `agent` y `applies_to`), agregar `pyyaml` a las dependencias y verificar con `tests/test_skills.py` (skill válida, inválida, reemplazo por nombre, selección por patrones y skill sin `applies_to`)
- [x] 10.2 Escribir las skills incluidas en `reviewer/skills/library/` moviendo ahí las listas de revisión de los prompts actuales (seguridad, diseño y funcional), dejar en cada agente solo el rol breve y verificar con un test que todas las skills incluidas son válidas y que cada agente tiene al menos una
- [x] 10.3 Cargar las skills del repo objetivo desde la rama base (API de GitHub en modo PR, `git` en modo local), con la nota cuando el PR modifica la carpeta y la nota de skills inválidas, y verificar con tests (`httpx.MockTransport` para la API y un repo git temporal para el modo local) que se usa la versión de la base
- [x] 10.4 Incluir las skills seleccionadas en el prompt de cada agente y registrar sus nombres en `AgentReport`, el resumen y el reporte JSON, y verificar con tests de agentes y de reporte
- [x] 10.5 Agregar la opción `skills_dir` (CLI, `REVIEWER_SKILLS_DIR`, entrada `skills-dir` de la Action), documentar el formato y la carpeta `.review-skills/` en README y `docs/DEPLOYMENT.md`, agregar `examples/review-skill-template.md`, y verificar que `ruff check .` y `pytest` pasan

## 11. Ajustes tras la primera prueba real

- [x] 11.1 Normalizar el endpoint de Azure OpenAI (quitar rutas como `/openai/v1/` que el portal muestra y que duplicaban la URL, causando 404) y verificar con `tests/test_llm.py`
- [x] 11.2 Unir duplicados entre agentes distintos (mismo archivo, ≤ 3 líneas, títulos similares ≥ 0,5) y verificar con `tests/test_aggregator.py` usando los títulos reales de la prueba (9 → 5 hallazgos)
- [x] 11.3 Agregar a los roles y a las reglas comunes la especialización por área y la coherencia del `summary` con los hallazgos, y verificar que `pytest` pasa
- [x] 11.4 Reforzar las skills `scope-and-claims` (verificar cada afirmación contra el diff), `acceptance-criteria` (la descripción no es prueba) y `hexagonal-layers` (controller que inyecta un repositorio = `major`), y verificar que todas las skills incluidas siguen siendo válidas
- [x] 11.5 Repetir la prueba local sobre la rama `prueba/revisor` y comparar contra los 8 errores sembrados (resultado: 6 de 8; el controller que usa el repositorio queda `major` y se detecta la falta de tests; la afirmación falsa sigue sin detectarse y la inyección SQL sigue duplicada, ver decisión 14)
- [x] 11.6 Unir duplicados entre agentes también por evidencia (líneas citadas, Jaccard ≥ 0,85) y verificar con `tests/test_aggregator.py` usando las citas reales de la segunda prueba (la misma consulta SQL se une; dos problemas que citan el mismo método no)
- [x] 11.7 Soportar modelos de razonamiento en Azure (detección por nombre o `REVIEWER_AZURE_REASONING_MODELS`, `max_completion_tokens`, `reasoning_effort`, sin `temperature`, versión de API `2025-04-01-preview`) y verificar con `tests/test_llm.py` la petición enviada en cada modo
- [x] 11.8 Agregar a la Action las entradas `model-functional`, `model-security`, `model-design` y `azure-reasoning-effort`, documentar la combinación recomendada en `docs/DEPLOYMENT.md`, y verificar con `tests/test_action.py`
- [ ] 11.9 Tercera prueba local con `REVIEWER_MODEL_FUNCTIONAL=gpt-5-mini` sobre la misma rama y comparar contra las dos anteriores (detecciones, duplicados y costo)

## Workflow follow-up

- Una vez validado, publicar `v1.0.0`, cambiar el repo objetivo a `@v1` con `fail-on: critical` y agregar el check a la protección de rama.
- Archivar el cambio con `/opsx:archive` cuando todas las tareas estén completas.
