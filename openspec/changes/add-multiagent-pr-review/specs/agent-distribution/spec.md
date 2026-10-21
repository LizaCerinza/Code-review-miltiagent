## Purpose

Empaquetar, publicar y versionar el revisor multiagente como imagen Docker, de forma que cualquier repositorio objetivo o entorno local lo despliegue con una versión conocida y pueda volver a una anterior.

## ADDED Requirements

### Requirement: Imagen ejecutable del revisor
El repositorio SHALL producir una imagen Docker cuyo punto de entrada es la CLI del revisor. La imagen MUST ejecutarse con un usuario sin privilegios de root y MUST recibir toda la configuración y las credenciales por variables de entorno en tiempo de ejecución, nunca incluirlas en la imagen.

#### Scenario: Ejecución sin argumentos de revisión
- **WHEN** se ejecuta la imagen con `--help`
- **THEN** muestra la ayuda de la CLI y termina con código 0

#### Scenario: Imagen sin secretos
- **WHEN** se inspeccionan las capas y variables de la imagen publicada
- **THEN** no contiene ninguna credencial de Azure OpenAI, Anthropic, GitHub ni Sonar

### Requirement: Publicación condicionada a la calidad
Una imagen MUST publicarse en GitHub Container Registry solo si en el mismo pipeline pasaron el lint, los tests y el escaneo de vulnerabilidades. Una vulnerabilidad de severidad crítica con corrección disponible MUST impedir la publicación.

#### Scenario: Tests fallidos
- **WHEN** se crea un tag de versión y algún test falla
- **THEN** no se publica ninguna imagen ni se crea el release

#### Scenario: Vulnerabilidad crítica
- **WHEN** el escaneo encuentra una vulnerabilidad crítica que tiene corrección disponible
- **THEN** el pipeline falla y la imagen no se publica

### Requirement: Validación en pull requests del propio repo
Cada pull request a este repositorio SHALL ejecutar el lint, los tests y la construcción de la imagen, sin publicarla.

#### Scenario: PR al revisor
- **WHEN** se abre un PR en este repositorio
- **THEN** el pipeline construye la imagen y ejecuta lint y tests, sin publicar nada en GHCR

### Requirement: Versionado semántico
Al crear un tag `vX.Y.Z`, el pipeline SHALL publicar la imagen con los tags `X.Y.Z`, `X.Y` y `X`, mover el tag de git `vX` al mismo commit y crear un GitHub Release con las notas de los cambios. Cada push a `main` SHALL publicar la imagen con el tag `edge`.

#### Scenario: Nueva versión menor
- **WHEN** se crea el tag `v1.2.0`
- **THEN** existen las imágenes `1.2.0`, `1.2` y `1` con el mismo digest
- **AND** el tag de git `v1` apunta al commit de `v1.2.0`
- **AND** existe el GitHub Release `v1.2.0`

#### Scenario: Push a main
- **WHEN** se integra un cambio en `main`
- **THEN** la imagen `edge` se actualiza y las imágenes versionadas no cambian

### Requirement: Ejecución local con la imagen
La imagen SHALL poder revisar un repositorio local montado como volumen, en modo local y sin publicar en GitHub, con el mismo comportamiento que la CLI instalada.

#### Scenario: Revisión local con Docker
- **WHEN** se ejecuta la imagen en modo local, montando el repo NestJS y pasando las credenciales de Azure OpenAI por variables de entorno
- **THEN** imprime el resumen de la revisión de `main...HEAD` y no hace llamadas de escritura a GitHub

### Requirement: Rollback por versión
Un repo objetivo SHALL poder volver a una versión anterior del revisor cambiando solo la referencia de la Action o de la imagen. Las versiones publicadas MUST NOT sobrescribirse.

#### Scenario: Volver a una versión anterior
- **WHEN** el repo objetivo cambia `@v1` por `@v1.1.0`
- **THEN** la siguiente ejecución usa exactamente la imagen `1.1.0` publicada originalmente

### Requirement: Guía de despliegue
El repositorio SHALL incluir una guía de despliegue con los pasos manuales necesarios: visibilidad pública del paquete en GHCR, secrets del repo objetivo, job de ejemplo, protección de rama, rotación de las credenciales del proveedor de modelos y rollback.

#### Scenario: Primer despliegue en un repo nuevo
- **WHEN** alguien sigue la guía en un repo objetivo que no tiene el revisor
- **THEN** al abrir un PR el revisor publica su resumen sin pasos adicionales no documentados
