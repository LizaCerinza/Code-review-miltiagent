# Guía de despliegue

El revisor corre en los runners de GitHub Actions del repo que se revisa, como una imagen Docker publicada en GitHub Container Registry (GHCR). No hay servidores propios: el único costo variable es el del proveedor de modelos (Azure OpenAI por defecto).

```text
Este repo (LizaCerinza/Code-review-miltiagent)        Repo objetivo (p. ej. farsov/Code-review-miltiagent)
─────────────────────────────────────────────        ─────────────────────────────────────────────────────
tag v1.2.0 ──► release.yml ──► ghcr.io/…:1.2.0         PR ──► ci.yml ──► job ai-review
                               ghcr.io/…:1.2                         uses: LizaCerinza/Code-review-miltiagent@v1
                               ghcr.io/…:1    ◄───────────────────── docker run ghcr.io/…:1
push a main ──► ci.yml ──────► ghcr.io/…:edge                        └► comenta en el PR
```

## 1. Publicar la primera versión (en este repo)

Requisitos: que el workflow `CI` esté en verde en `main`.

1. Crea y sube el tag:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
2. En **Actions → Release**, espera a que termine. El workflow corre los tests, construye la imagen, la escanea con Trivy y publica `ghcr.io/lizacerinza/code-review-miltiagent` con los tags `0.1.0`, `0.1` y `0`. También mueve el tag de git `v0` y crea el GitHub Release.
3. **Haz público el paquete (una sola vez).** GHCR crea los paquetes como privados, y un repo de otra cuenta no puede descargarlos. Ve a tu perfil → **Packages** → `code-review-miltiagent` → **Package settings** → **Change visibility** → **Public**.
4. Comprueba que se puede descargar sin autenticación:
   ```bash
   docker pull ghcr.io/lizacerinza/code-review-miltiagent:0
   ```

Cada versión nueva repite los pasos 1 y 2. El tag `X.Y.Z` nunca se sobrescribe: si el release falla a medias, publica un tag nuevo (`v0.1.1`).

## 2. Instalar el revisor en un repo objetivo

### 2.0 Recurso de Azure OpenAI y deployment

Una sola vez, en el portal de Azure:

1. Crea un recurso **Azure OpenAI** (o Azure AI Foundry) en una región que ofrezca `gpt-4.1-mini`.
2. En **Azure AI Foundry → Deployments → Deploy model**, despliega `gpt-4.1-mini`. El **nombre del deployment** es lo que va en la entrada `model` de la Action; si lo llamas `gpt-4.1-mini`, no hay que cambiar nada.
3. Anota el **endpoint** (`https://<recurso>.openai.azure.com`) y una de las dos **keys** (**Resource Management → Keys and Endpoint**).
4. Recomendado: revisa la cuota de tokens por minuto del deployment (cada revisión manda tres peticiones a la vez) y configura una alerta de presupuesto en la suscripción.

### 2.1 Secrets y variables

En el repo objetivo: **Settings → Secrets and variables → Actions**.

| Nombre | Tipo | Obligatorio | Valor |
| --- | --- | --- | --- |
| `AZURE_OPENAI_API_KEY` | Secret | Sí (con `provider: azure`) | Key del recurso de Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | Variable (o secret) | Sí (con `provider: azure`) | `https://<recurso>.openai.azure.com` |
| `ANTHROPIC_API_KEY` | Secret | Solo con `provider: anthropic` | API key de Claude ([console.anthropic.com](https://console.anthropic.com)) |
| `SONAR_TOKEN` | Secret | No | El mismo token que usa el job de Sonar. Sin él, el agente de seguridad no puede descartar los issues que Sonar ya reportó |

`GITHUB_TOKEN` no se configura: el workflow lo provee automáticamente.

### 2.2 Tareas

Crea la carpeta `docs/tasks/` y agrega una tarea por funcionalidad, usando [`examples/task-template.md`](../examples/task-template.md) como plantilla. En la descripción de cada PR va el hashtag con el nombre del archivo:

```text
Implementa la gestión de roles. #add-user-roles
```

Un PR sin hashtag, o con un hashtag que no corresponde a ningún archivo, recibe un hallazgo `critical`.

### 2.3 Guías de diseño

Completa `REVIEW_GUIDELINES.md` (arquitectura, convenciones y qué se considera crítico). Si está vacío, el agente de diseño usa las convenciones que ve en el código y lo avisa en el resumen.

### 2.3b Skills propias del equipo (opcional)

Para reglas que el equipo quiere que los agentes revisen siempre, crea skills en `.review-skills/<nombre>/SKILL.md` a partir de [`examples/review-skill-template.md`](../examples/review-skill-template.md):

- `agent` indica qué agente la recibe (`functional`, `security`, `design` o `all`).
- `applies_to` limita la skill a ciertos archivos. Por ejemplo, `["src/**/*.controller.ts"]` solo se activa en PRs que tocan controllers.
- Si `name` coincide con una skill incluida en el revisor (ver la tabla del README), la reemplaza.

Las skills se leen de la **rama base** del PR. Cuando agregues o cambies una, el efecto empieza en los PRs siguientes al merge. El resumen avisa cuando un PR modifica skills, e ignora (con aviso) las que tienen un formato inválido.

### 2.4 Job en el workflow

Copia el job de [`examples/ai-review-job.yml`](../examples/ai-review-job.yml) dentro de `jobs:` en `.github/workflows/ci.yml` del repo objetivo. Puntos importantes:

- `needs: quality`: el revisor corre después de Sonar, así sus issues ya existen.
- `permissions`: solo `contents: read` y `pull-requests: write`.
- El checkout usa `ref: ${{ github.event.pull_request.head.sha }}`.
- Usa el evento `pull_request`. **No** uses `pull_request_target`: ejecutaría el contenido del PR con acceso a los secrets.

### 2.5 Adopción gradual

1. Empieza con `fail-on: none`: el revisor comenta pero nunca bloquea.
2. Abre algunos PRs con defectos conocidos y revisa la calidad de los hallazgos.
3. Cuando el equipo confíe en el revisor, cambia a `fail-on: critical`.
4. En **Settings → Branches**, agrega el check **AI review (multiagente)** como obligatorio en `main`.

## 3. Entradas de la Action

| Entrada | Por defecto | Descripción |
| --- | --- | --- |
| `provider` | `azure` | `azure` (Azure OpenAI) o `anthropic` (Claude) |
| `azure-openai-api-key` / `azure-openai-endpoint` | — | Credenciales de Azure. Si llegan vacías (PR desde un fork), la revisión se omite sin fallar |
| `azure-openai-api-version` | `2024-10-21` | Versión de la API de Azure OpenAI (debe soportar salidas estructuradas) |
| `anthropic-api-key` | — | Solo con `provider: anthropic` |
| `github-token` | `github.token` | Lectura del PR y comentarios |
| `sonar-token` / `sonar-host-url` | — / `https://sonarcloud.io` | Issues de Sonar del PR |
| `fail-on` | `critical` | `critical`, `major`, `minor`, `info` o `none` |
| `fail-on-agent-error` | `false` | Falla el paso si algún agente no termina |
| `model` | `gpt-4.1-mini` / `claude-opus-5-5` | Modelo de los tres agentes; en Azure, el nombre del deployment |
| `model-functional` / `model-security` / `model-design` | — | Modelo o deployment para un solo agente (reemplaza a `model` para ese agente) |
| `azure-reasoning-effort` | `medium` | Esfuerzo de razonamiento de los deployments `gpt-5*` y `o1`/`o3`/`o4*` |
| `agent-timeout` | `600` | Segundos máximos por agente |
| `tasks-dir` | `docs/tasks` | Carpeta de las tareas |
| `spec-globs` | `openspec/specs/**/*.md` | Especificaciones, separadas por comas |
| `guidelines-file` | `REVIEW_GUIDELINES.md` | Estándares de diseño |
| `skills-dir` | `.review-skills` | Skills propias del repo (leídas de la rama base) |
| `image` | según la versión | Fuerza una imagen concreta |

Salida: `report-path`, la ruta del reporte JSON (para subirlo como artefacto).

## 4. Operación

### Versiones y rollback

| Referencia en `uses:` | Imagen | Uso |
| --- | --- | --- |
| `@v1` | `1` | Recomendado: recibe las versiones menores y de parche |
| `@v1.2.0` | `1.2.0` | Fijar una versión exacta (rollback) |
| `@main` | `edge` | Probar cambios sin publicar una versión |

Rollback: cambia `@v1` por la última versión buena (`@v1.1.0`). La imagen es la misma que se publicó en su momento. Para desactivar el revisor de inmediato: `fail-on: none`, o quita el job.

### Rotar la key de Azure OpenAI

Azure da dos keys por recurso para rotar sin cortes:

1. Cambia el secret `AZURE_OPENAI_API_KEY` de cada repo objetivo a la **KEY 2**.
2. En **Keys and Endpoint**, regenera la **KEY 1**.
3. En la próxima rotación, haz lo mismo al revés.

Con Claude: crea una key nueva en la consola de Anthropic, actualiza `ANTHROPIC_API_KEY` y revoca la anterior.

### Trazas con LangSmith (opcional)

La orquestación es un grafo de LangGraph. Si defines en el job las variables `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` (desde un secret) y `LANGSMITH_PROJECT`, la Action las pasa al contenedor y cada revisión queda trazada en LangSmith, con un nodo por agente.

### Costos

Cada ejecución hace tres llamadas al modelo, y cada push a un PR abierto la repite. El reporte JSON incluye los tokens de entrada y salida de cada agente. `gpt-4.1-mini` es la opción económica.

**Combinación recomendada (costo/beneficio):** `gpt-5-mini` solo para el agente funcional y `gpt-4.1-mini` para seguridad y diseño, unos 1 a 2 centavos de dólar por PR. En las pruebas, `gpt-4.1-mini` detectó bien los problemas concretos (inyección SQL, validaciones, capas), pero no verificaba las afirmaciones de la descripción del PR: esa tarea necesita un modelo de razonamiento. Crea los dos deployments en el recurso y configura:

```yaml
with:
  model: gpt-4.1-mini
  model-functional: gpt-5-mini
```

Los deployments de razonamiento (nombres que empiezan con `gpt-5`, `o1`, `o3` u `o4`) se invocan automáticamente con los parámetros que aceptan y con la versión de la API `2025-04-01-preview`. Si tu deployment tiene otro nombre, decláralo con la variable `REVIEWER_AZURE_REASONING_MODELS`.

### Uso local con Docker

```bash
docker run --rm \
  -e AZURE_OPENAI_API_KEY -e AZURE_OPENAI_ENDPOINT \
  -v "$(pwd):/workspace:ro" \
  -v "$(pwd)/.ai-review:/output" -e REVIEWER_OUTPUT_DIR=/output \
  ghcr.io/lizacerinza/code-review-miltiagent:0 \
  --local --base main --workspace /workspace
```

Revisa `main...HEAD` del repo actual e imprime el resumen, sin publicar nada en GitHub.

## 5. Solución de problemas

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `No se pudo descargar ghcr.io/…` | El paquete de GHCR es privado | Paso 1.3: hazlo público |
| `No hay una imagen publicada para '@<rama>'` | La Action se referenció con una rama o un SHA | Usa `@vX`, `@main` o la entrada `image` |
| "Code review multiagente omitido" | PR desde un fork: GitHub no le entrega secrets | Es el comportamiento esperado; revisa el PR a mano o recréalo desde una rama del repo |
| `Resource not accessible by integration` (403) | El job no tiene `pull-requests: write` | Agrega el permiso en el job |
| Código de salida 2 con `faltan las credenciales del proveedor` | Secret o variable vacíos en un PR del mismo repo | Revisa los nombres y que el job los pase en `azure-openai-api-key` y `azure-openai-endpoint` |
| Agente con error `NotFoundError` (deployment no encontrado) | El nombre del deployment no coincide con `model` | Usa en `model` el nombre exacto del deployment |
| Agente con error `AuthenticationError` (401) | Key incorrecta o de otro recurso | Copia de nuevo la key y el endpoint del mismo recurso |
| Agente con error `RateLimitError` (429) | La cuota de tokens por minuto del deployment no alcanza | Sube la cuota del deployment |
| Agente con error "filtro de contenido" | El filtro de Azure bloqueó el prompt o la respuesta (puede pasar con código o hallazgos de seguridad) | La revisión queda incompleta, no aprobada; si es frecuente, ajusta la política de filtros del deployment |
| "Revisión incompleta" | Un agente superó el tiempo o la API falló | Vuelve a ejecutar el job; si se repite, sube `agent-timeout` |
| Comentarios inline ausentes, solo el resumen | GitHub rechazó alguna línea (422), por ejemplo si se forzó un push durante la revisión | Ejecuta el job de nuevo; el resumen siempre tiene todos los hallazgos |
