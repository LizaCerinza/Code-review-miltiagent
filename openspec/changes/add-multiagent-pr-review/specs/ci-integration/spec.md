## Purpose

Permitir que un repositorio objetivo invoque el revisor multiagente desde su pipeline de GitHub Actions como un paso más, con entradas, permisos y modos de fallo bien definidos.

## ADDED Requirements

### Requirement: Action reutilizable
Este repositorio SHALL publicar una GitHub Action que un repo objetivo pueda usar con `uses: <owner>/<repo>@<ref>`. La Action ejecuta la imagen publicada que corresponde a su misma referencia, sin reconstruir ni reinstalar el revisor en cada ejecución.

#### Scenario: Uso desde el repo objetivo
- **WHEN** el workflow del repo objetivo tiene un paso con `uses: LizaCerinza/Code-review-miltiagent@v1` en un evento `pull_request`
- **THEN** el revisor ejecuta la imagen `1`, revisa ese PR y publica el resultado en él

#### Scenario: Imagen forzada
- **WHEN** se pasa la entrada `image` con una imagen concreta
- **THEN** la Action ejecuta esa imagen en lugar de la que corresponde a su referencia

### Requirement: Entradas configurables
La Action SHALL aceptar como entradas: token de GitHub (por defecto, el del workflow), token y URL de Sonar (opcionales), umbral de bloqueo, fallar por error de agente, modelo o deployment, carpeta de tareas, glob de especificaciones, archivo de estándares, carpeta de skills e imagen. Cada entrada opcional SHALL tener un valor por defecto documentado.

#### Scenario: Valores por defecto
- **WHEN** solo se pasan la API key y el endpoint de Azure OpenAI
- **THEN** el revisor usa el proveedor `azure` con el deployment `gpt-4.1-mini`, el umbral `critical`, la carpeta `docs/tasks/`, las especificaciones `openspec/specs/**/*.md` y el archivo `REVIEW_GUIDELINES.md`

### Requirement: Entradas del proveedor de modelos
La Action SHALL aceptar el proveedor de modelos (`azure` por defecto o `anthropic`) y sus credenciales: API key, endpoint y versión de la API de Azure OpenAI, o la API key de Anthropic. Solo las credenciales del proveedor elegido son obligatorias.

#### Scenario: Proveedor Anthropic
- **WHEN** se pasa `provider: anthropic` y la API key de Anthropic, sin credenciales de Azure
- **THEN** el revisor usa Claude y no exige las credenciales de Azure

### Requirement: Solo en eventos de pull request
La Action SHALL revisar solo en eventos de pull request. En cualquier otro evento MUST terminar con éxito, avisar que no hay PR que revisar y no llamar al proveedor de modelos.

#### Scenario: Push a main
- **WHEN** la Action se ejecuta en un evento `push`
- **THEN** termina con código 0 y un aviso, sin llamar al proveedor de modelos

### Requirement: PRs desde forks sin secretos
Cuando el PR viene de un fork y la credencial del proveedor de modelos elegido no está disponible, la Action SHALL omitir la revisión con un aviso explícito, sin bloquear ni fallar el job.

#### Scenario: PR externo
- **WHEN** se abre un PR desde un fork y el secret `AZURE_OPENAI_API_KEY` llega vacío
- **THEN** el job termina con éxito y el resumen del job explica que la revisión se omitió

### Requirement: Permisos mínimos
La Action SHALL funcionar con los permisos `contents: read` y `pull-requests: write`, y con el evento `pull_request`. MUST NOT requerir `pull_request_target` ni permisos de escritura sobre el contenido del repositorio.

#### Scenario: Job con permisos mínimos
- **WHEN** el job declara solo `contents: read` y `pull-requests: write`
- **THEN** la revisión se publica sin errores de permisos

### Requirement: Imagen y Action privadas
El revisor SHALL poder usarse sin hacer públicos su repositorio ni su paquete en GHCR. Para descargar una imagen de `ghcr.io`, la Action MUST autenticarse con el token del workflow, pasado por entrada estándar y nunca como argumento. Si la descarga falla, la Action SHALL construir la imagen desde su propio código, en la misma versión, y avisarlo en el log.

#### Scenario: Paquete privado con acceso concedido
- **WHEN** el paquete es privado, el repo objetivo tiene acceso de lectura en el paquete y el job declara `packages: read`
- **THEN** la Action descarga la imagen y ejecuta la revisión

#### Scenario: Paquete privado sin acceso
- **WHEN** el paquete es privado y el repo objetivo no tiene acceso de lectura (por ejemplo, un paquete de una cuenta personal, que no ofrece "Manage Actions access")
- **THEN** la Action construye la imagen desde su código, ejecuta la revisión y deja un aviso que explica cómo usar la imagen publicada

### Requirement: Resultado visible en el job
La Action SHALL escribir el resumen de la revisión en el resumen del job de GitHub Actions y dejar el reporte JSON disponible para subirlo como artefacto. El estado del paso SHALL reflejar el código de salida del revisor.

#### Scenario: Revisión bloqueante
- **WHEN** el revisor termina con código 1
- **THEN** el paso aparece como fallido y el resumen del job muestra los hallazgos bloqueantes

### Requirement: Tiempo máximo de ejecución
El revisor SHALL respetar un tiempo máximo configurable por agente. Un agente que lo supere se trata como agente con error, según los requisitos de orquestación.

#### Scenario: Agente lento
- **WHEN** un agente supera el tiempo máximo
- **THEN** se cancela y la revisión se publica como "incompleta", con los resultados de los demás agentes
