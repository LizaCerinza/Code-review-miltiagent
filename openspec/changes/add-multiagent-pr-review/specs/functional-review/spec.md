## Purpose

Verificar que un pull request implementa lo que pide la tarea en Markdown que referencia y que no rompe las especificaciones vigentes del repositorio objetivo.

## ADDED Requirements

### Requirement: Resolución de la tarea por hashtag
El revisor SHALL buscar en el título y la descripción del PR hashtags de la forma `#<nombre>`, donde `<nombre>` no es solo numérico. Cada uno SHALL resolverse al archivo `<nombre>.md` dentro de la carpeta de tareas configurada (por defecto `docs/tasks/`). Los hashtags numéricos (`#123`) se ignoran, porque son referencias a issues.

#### Scenario: PR con hashtag válido
- **WHEN** la descripción del PR contiene `#add-user-roles` y existe `docs/tasks/add-user-roles.md`
- **THEN** el agente funcional recibe el contenido de `add-user-roles.md` como la tarea a validar

#### Scenario: Hashtag con extensión
- **WHEN** la descripción contiene `#add-user-roles.md`
- **THEN** se resuelve al mismo archivo `docs/tasks/add-user-roles.md`

#### Scenario: Referencia a issue
- **WHEN** la descripción contiene solo `Closes #12`
- **THEN** `#12` no se interpreta como tarea

#### Scenario: Varias tareas
- **WHEN** el PR referencia `#tarea-a` y `#tarea-b` y ambos archivos existen
- **THEN** el agente valida el PR contra las dos tareas

### Requirement: Tarea ausente o inexistente
Si el PR no referencia ninguna tarea, o si una tarea referenciada no existe en la carpeta de tareas, el revisor MUST publicar un hallazgo `critical` con confianza `high` que lo explique. Ese hallazgo bloquea el merge, porque sin tarea no se puede validar la funcionalidad.

#### Scenario: PR sin hashtag
- **WHEN** ni el título ni la descripción del PR contienen un hashtag de tarea
- **THEN** se publica un hallazgo `critical` "PR sin tarea referenciada" que indica el formato esperado

#### Scenario: Archivo inexistente
- **WHEN** la descripción contiene `#tarea-x` y no existe `docs/tasks/tarea-x.md`
- **THEN** se publica un hallazgo `critical` que nombra la ruta buscada

### Requirement: Validación de criterios de la tarea
El agente funcional SHALL evaluar cada requisito o criterio de aceptación de la tarea frente al código cambiado y clasificarlo como "cumple", "no cumple" o "no verificable". Cada criterio que no se cumple MUST reportarse como hallazgo con la evidencia del código. El resumen del agente MUST listar el estado de cada criterio.

#### Scenario: Criterio incumplido
- **WHEN** la tarea exige "responder 409 si el email ya existe" y el código responde 500 en ese caso
- **THEN** se reporta un hallazgo `critical` que cita el criterio y el código responsable

#### Scenario: Criterio afirmado solo en la descripción
- **WHEN** la descripción del PR dice "limita los resultados a 20" y el código no aplica ningún límite
- **THEN** el criterio se clasifica como "no cumple", no como "cumple"

#### Scenario: Criterio no verificable
- **WHEN** un criterio depende de código que no forma parte del PR ni de su contexto
- **THEN** el criterio figura como "no verificable" en el resumen, sin hallazgo bloqueante

### Requirement: Cambios fuera del alcance de la tarea
El agente funcional SHALL reportar como hallazgo `major` los cambios de comportamiento del PR que ninguna tarea referenciada justifica.

#### Scenario: Cambio no solicitado
- **WHEN** la tarea pide agregar un endpoint y el PR además cambia la validación de un endpoint existente
- **THEN** se reporta un hallazgo `major` "cambio fuera del alcance de la tarea" en el código afectado

### Requirement: Coherencia con las especificaciones vigentes
El agente funcional SHALL recibir las especificaciones del repo objetivo (por defecto `openspec/specs/**/*.md`) y reportar como hallazgo `critical` cualquier cambio que contradiga un requisito o escenario vigente que la tarea no modifica explícitamente.

#### Scenario: Regresión contra un spec
- **WHEN** un spec vigente exige "DELETE /users/:id responde 204" y el PR lo cambia a 200 sin que la tarea lo pida
- **THEN** se reporta un hallazgo `critical` que referencia el requisito del spec

### Requirement: Afirmaciones no respaldadas en la descripción del PR
El agente funcional SHALL reportar como hallazgo `major` toda afirmación de la descripción del PR sobre lo implementado o probado que el diff no respalda.

#### Scenario: Descripción que afirma tests inexistentes
- **WHEN** la descripción dice "agregué tests para el caso 409" y el diff no contiene ningún test de ese caso
- **THEN** se reporta un hallazgo `major` que cita la afirmación

### Requirement: Cobertura de pruebas de los criterios
El agente funcional SHALL reportar como hallazgo `minor` cada criterio de la tarea que se cumple pero no tiene una prueba en el PR que lo verifique.

#### Scenario: Criterio sin test
- **WHEN** un criterio se implementa correctamente y ningún test del PR cubre ese escenario
- **THEN** se reporta un hallazgo `minor` que sugiere el test faltante
