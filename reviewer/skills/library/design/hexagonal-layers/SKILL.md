---
name: hexagonal-layers
agent: design
description: Responsabilidades por capa en la arquitectura hexagonal
applies_to: ["src/**"]
---
Capas: `domain` (entidades, puertos, errores de dominio; no depende de nada) → `application`
(casos de uso; solo depende del dominio) → `infrastructure` (HTTP, persistencia, módulos de
NestJS). ESLint ya bloquea los imports prohibidos entre capas; tú revisa lo que el linter no ve
(category `layering`):
- **Controllers que saltan la capa de aplicación**: un controller que inyecta un repositorio o
  puerto (`@Inject(USER_REPOSITORY)`, `UserRepositoryPort`) y lo llama directamente, en lugar de
  invocar un caso de uso. Es `major`: rompe el flujo controller → caso de uso → puerto.
- Reglas de negocio (unicidad, permisos, cálculos, transiciones de estado, filtrado, ordenamiento,
  límites, normalización de datos) en controllers, DTOs, mappers, adaptadores de persistencia o
  filtros, en lugar de en el caso de uso o el dominio. Un controller solo traduce la petición,
  llama a un caso de uso y devuelve el resultado.
- Casos de uso que reciben o devuelven tipos de framework (DTOs con decoradores, entidades ORM,
  `Request`) en lugar de tipos de dominio.
- Excepciones HTTP (`NotFoundException`, `HttpException`) lanzadas desde el dominio o los casos de
  uso, en lugar de errores de dominio que traduce un filtro.
- Adaptadores que deciden reglas de negocio en lugar de solo traducir y persistir.

Las violaciones que rompen la arquitectura (el dominio dependiendo de infraestructura) son
`critical`; el resto, `major` o `minor`.
