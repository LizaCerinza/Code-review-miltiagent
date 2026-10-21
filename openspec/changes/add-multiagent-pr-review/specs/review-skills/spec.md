## Purpose

Empaquetar el conocimiento de revisión de cada agente en skills: archivos Markdown versionados que el revisor selecciona según los archivos que cambia el PR, y que cada repositorio objetivo puede ampliar con sus propias reglas.

## ADDED Requirements

### Requirement: Formato de una skill
Una skill SHALL ser un archivo `SKILL.md` con un encabezado YAML que declara `name`, `agent` (`functional`, `security`, `design` o `all`), `description` y, opcionalmente, `applies_to` (lista de patrones glob de rutas). El cuerpo Markdown contiene las instrucciones de revisión.

#### Scenario: Skill válida
- **WHEN** un `SKILL.md` declara `name: ci-workflows`, `agent: security`, una descripción y `applies_to: [".github/**"]`
- **THEN** el revisor la carga como skill del agente de seguridad para archivos bajo `.github/`

#### Scenario: Skill del repo inválida
- **WHEN** una skill del repo objetivo no tiene `name` o declara un `agent` desconocido
- **THEN** el revisor la ignora y el resumen del PR indica qué archivo se ignoró y por qué

### Requirement: Selección según los archivos del PR
Para cada agente, el revisor SHALL incluir en su prompt solo las skills de ese agente (o de `all`) que no declaran `applies_to` o cuyo `applies_to` coincide con al menos un archivo cambiado del PR.

#### Scenario: PR que solo toca un controller
- **WHEN** el PR modifica únicamente `src/users/infrastructure/http/users.controller.ts`
- **THEN** el agente de seguridad no recibe la skill de workflows de CI

#### Scenario: PR que toca un workflow
- **WHEN** el PR modifica `.github/workflows/ci.yml`
- **THEN** el agente de seguridad recibe la skill de workflows de CI

### Requirement: Skills incluidas en el revisor
El revisor SHALL incluir skills propias para cada agente, que cubran como mínimo las áreas de revisión definidas en las especificaciones de los agentes funcional, de seguridad y de diseño.

#### Scenario: Ejecución sin skills del repo
- **WHEN** el repo objetivo no tiene carpeta de skills
- **THEN** cada agente revisa con las skills incluidas en el revisor

### Requirement: Skills del repositorio objetivo
El revisor SHALL cargar además las skills de la carpeta configurada del repo objetivo (por defecto `.review-skills/`). Una skill del repo con el mismo `name` que una incluida SHALL reemplazarla.

#### Scenario: Regla propia del equipo
- **WHEN** el repo objetivo tiene `.review-skills/naming/SKILL.md` con `agent: design`
- **THEN** el agente de diseño recibe esa skill junto con las incluidas

#### Scenario: Reemplazo de una skill incluida
- **WHEN** el repo objetivo define una skill con el mismo `name` que una incluida
- **THEN** el agente recibe la versión del repo y no la incluida

### Requirement: Skills del repo leídas de la rama base
Las skills del repo objetivo MUST leerse de la rama base del PR y nunca de los cambios del propio PR, para que un PR no pueda debilitar la revisión que se le aplica. Si el PR modifica la carpeta de skills, el resumen SHALL indicar que esos cambios se aplicarán después del merge.

#### Scenario: PR que debilita una skill
- **WHEN** un PR edita `.review-skills/security-rules/SKILL.md` para eliminar una regla
- **THEN** la revisión de ese PR usa la versión de la rama base, con la regla
- **AND** el resumen avisa que el PR modifica skills de revisión

### Requirement: Registro de las skills usadas
El reporte de cada agente SHALL listar las skills que recibió, en el resumen publicado y en el reporte JSON.

#### Scenario: Reporte de una ejecución
- **WHEN** termina una revisión
- **THEN** el reporte JSON de cada agente incluye los nombres de sus skills
