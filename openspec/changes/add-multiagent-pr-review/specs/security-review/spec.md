## Purpose

Detectar en un pull request los problemas de seguridad que un análisis estático por reglas como Sonar no encuentra, sin repetir lo que Sonar ya reportó.

## ADDED Requirements

### Requirement: No duplicar los issues de Sonar
Cuando Sonar esté configurado, el agente de seguridad SHALL recibir los issues abiertos que Sonar reportó en el PR y MUST NOT reportar de nuevo un problema que Sonar ya señaló en el mismo archivo y la misma zona de código.

#### Scenario: Issue ya reportado por Sonar
- **WHEN** Sonar reportó un secreto en el código en `src/config/env.config.ts:10`
- **THEN** el agente de seguridad no publica un hallazgo sobre ese mismo secreto

### Requirement: Revisión sin Sonar disponible
Si Sonar no está configurado o su API falla, el agente de seguridad SHALL hacer la revisión igualmente y el resumen MUST indicar que no se pudieron descartar los duplicados de Sonar.

#### Scenario: API de Sonar caída
- **WHEN** la consulta a Sonar devuelve un error
- **THEN** la revisión de seguridad se completa
- **AND** el resumen indica "issues de Sonar no disponibles"

### Requirement: Control de acceso y autorización
El agente de seguridad SHALL detectar endpoints o casos de uso nuevos o modificados que permitan operar sin la autenticación o autorización requeridas, incluido el acceso a recursos de otro usuario manipulando un identificador (IDOR).

#### Scenario: Endpoint sin guard
- **WHEN** el PR agrega un endpoint que modifica datos sin el guard de autenticación que usan los endpoints equivalentes
- **THEN** se reporta un hallazgo de categoría `broken-access-control` que describe cómo explotarlo

### Requirement: Validación de entrada y asignación masiva
El agente de seguridad SHALL detectar entradas que llegan a la lógica o a la persistencia sin validar: DTOs sin restricciones, propiedades no declaradas que se aceptan, valores `null` que llegan a columnas obligatorias y objetos de la petición copiados directamente sobre entidades.

#### Scenario: Asignación masiva
- **WHEN** el PR copia el body completo de la petición sobre una entidad que tiene un campo `role`
- **THEN** se reporta un hallazgo de categoría `mass-assignment`

### Requirement: Exposición de datos sensibles
El agente de seguridad SHALL detectar datos sensibles (contraseñas, tokens, datos personales, detalles internos de errores) expuestos en respuestas HTTP, logs o mensajes de error.

#### Scenario: Hash de contraseña en la respuesta
- **WHEN** un endpoint devuelve la entidad de usuario completa, con su campo de contraseña
- **THEN** se reporta un hallazgo de categoría `sensitive-data-exposure`

### Requirement: Inyección en contextos no cubiertos por reglas
El agente de seguridad SHALL detectar consultas, rutas de archivo, comandos o encabezados construidos con datos del usuario cuando el patrón no sea uno que Sonar reconoce, como SQL armado a través de varias funciones.

#### Scenario: Consulta construida con interpolación
- **WHEN** el PR arma una consulta SQL interpolando un parámetro de la petición en un helper
- **THEN** se reporta un hallazgo de categoría `injection` con el flujo del dato hasta la consulta

### Requirement: Lógica de negocio explotable
El agente de seguridad SHALL detectar condiciones de carrera del tipo "verificar y luego actuar", validaciones que el cliente puede saltarse y reglas de negocio que se pueden eludir.

#### Scenario: Verificar y luego actuar sin restricción
- **WHEN** el PR comprueba que un recurso no existe y luego lo crea, sin una restricción única ni una transacción
- **THEN** se reporta un hallazgo de categoría `race-condition`

### Requirement: Configuración y cadena de suministro
El agente de seguridad SHALL revisar los cambios en configuración, workflows de CI y dependencias: permisos amplios, `pull_request_target`, secretos expuestos al código del PR, CORS abierto, sincronización de esquema en producción, y dependencias nuevas inexistentes, con nombre sospechosamente parecido a uno popular o con scripts de instalación.

#### Scenario: Dependencia con nombre sospechoso
- **WHEN** el PR agrega a `package.json` una dependencia cuyo nombre es casi igual al de un paquete popular
- **THEN** se reporta un hallazgo de categoría `supply-chain` que pide verificar el paquete

#### Scenario: Workflow con secretos expuestos
- **WHEN** el PR cambia un workflow a `pull_request_target` y ejecuta código del PR con secretos disponibles
- **THEN** se reporta un hallazgo `critical` de categoría `ci-security`

### Requirement: Controles de seguridad debilitados
El agente de seguridad SHALL reportar los cambios que desactivan o debilitan controles existentes: validaciones eliminadas, guards quitados, reglas de lint de seguridad deshabilitadas, tests de seguridad eliminados u omitidos.

#### Scenario: Validación eliminada
- **WHEN** el PR quita `forbidNonWhitelisted` del `ValidationPipe` global
- **THEN** se reporta un hallazgo de categoría `weakened-control`

### Requirement: Severidad basada en explotabilidad
El agente de seguridad MUST usar severidad `critical` solo cuando el problema sea explotable de forma realista, y MUST describir en la explicación el camino de explotación.

#### Scenario: Problema teórico
- **WHEN** un problema solo sería explotable si se cumplieran condiciones que el código actual no permite
- **THEN** el hallazgo tiene severidad `minor` o `info`, no `critical`
