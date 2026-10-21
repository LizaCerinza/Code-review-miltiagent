## Purpose

Verificar que el código de un pull request respeta la arquitectura, los patrones y los estándares definidos para el repositorio objetivo, en todo lo que el linter no puede comprobar.

## ADDED Requirements

### Requirement: Estándares del repositorio como referencia principal
El agente de diseño SHALL usar como referencia principal el archivo de estándares del repo objetivo (por defecto `REVIEW_GUIDELINES.md`). Cada hallazgo MUST citar la regla, el principio o el patrón que incumple.

#### Scenario: Regla de las guías incumplida
- **WHEN** las guías dicen "los casos de uso no dependen de NestJS" y el PR importa `@nestjs/common` en un caso de uso
- **THEN** se reporta un hallazgo que cita esa regla de las guías

### Requirement: Guías vacías o ausentes
Si el archivo de estándares no existe o está vacío, el agente de diseño SHALL tomar como referencia las convenciones que ya muestra el código del repositorio, y su resumen MUST indicar que no había guías definidas.

#### Scenario: REVIEW_GUIDELINES.md vacío
- **WHEN** el archivo de estándares solo tiene títulos sin contenido
- **THEN** el agente revisa según los patrones existentes en el código
- **AND** su resumen indica "sin guías definidas: se usaron las convenciones del código"

### Requirement: Sin duplicar el linter
El agente de diseño MUST NOT reportar formato, orden de imports, reglas de tipado ni restricciones de importación entre capas que el linter del repo ya hace cumplir.

#### Scenario: Problema de formato
- **WHEN** el PR tiene una línea mal indentada
- **THEN** el agente de diseño no reporta nada sobre ella

### Requirement: Responsabilidades por capa
El agente de diseño SHALL detectar lógica ubicada en la capa equivocada de la arquitectura hexagonal: reglas de negocio en controllers, adaptadores o DTOs; dominio que depende de detalles de framework o de persistencia; casos de uso que acceden directamente a la infraestructura.

#### Scenario: Regla de negocio en el controller
- **WHEN** el PR agrega al controller la verificación de que el email no está duplicado, en lugar de hacerla en el caso de uso
- **THEN** se reporta un hallazgo de categoría `layering`

### Requirement: Consistencia con los patrones existentes
El agente de diseño SHALL reportar el código que resuelve un problema distinto de como ya lo resuelve el repositorio: errores de dominio, mappers, puertos y adaptadores, DTOs de respuesta o registro de módulos.

#### Scenario: Excepción HTTP en el dominio
- **WHEN** el repo traduce errores de dominio a HTTP con un filtro y el PR lanza `NotFoundException` desde un caso de uso
- **THEN** se reporta un hallazgo de categoría `pattern-consistency` que señala el patrón existente

### Requirement: Reutilización y código innecesario
El agente de diseño SHALL reportar la lógica que duplica utilidades o abstracciones ya existentes, el código muerto o sin uso y las abstracciones que el cambio no necesita.

#### Scenario: Helper duplicado
- **WHEN** el PR agrega una función de validación que ya existe en otro módulo del repo
- **THEN** se reporta un hallazgo de categoría `duplication` que nombra la implementación existente

#### Scenario: Abstracción especulativa
- **WHEN** el PR agrega una interfaz con una sola implementación que nada más usa ni planea usar
- **THEN** se reporta un hallazgo `minor` de categoría `over-engineering`

### Requirement: Principios de diseño
El agente de diseño SHALL detectar violaciones relevantes de SOLID, cohesión y acoplamiento en el código cambiado, como clases o casos de uso con varias responsabilidades o dependencias de implementaciones concretas donde el proyecto usa puertos.

#### Scenario: Caso de uso con varias responsabilidades
- **WHEN** un caso de uso nuevo crea un usuario, envía un email y escribe un log de auditoría
- **THEN** se reporta un hallazgo de categoría `single-responsibility`

### Requirement: Contratos públicos y compatibilidad
El agente de diseño SHALL reportar los cambios que rompen contratos públicos, como la forma de las respuestas de la API, firmas de puertos o nombres de rutas, sin que la tarea del PR lo justifique.

#### Scenario: Campo eliminado de la respuesta
- **WHEN** el PR quita un campo del DTO de respuesta de un endpoint existente
- **THEN** se reporta un hallazgo de categoría `breaking-change`

### Requirement: Pruebas en la capa adecuada
El agente de diseño SHALL reportar el comportamiento nuevo sin pruebas en la capa donde vive la lógica (por ejemplo, un caso de uso nuevo sin test unitario) y las pruebas que verifican la implementación interna en vez del comportamiento.

#### Scenario: Caso de uso sin test
- **WHEN** el PR agrega un caso de uso y ningún test unitario lo ejecuta
- **THEN** se reporta un hallazgo de categoría `testing`
