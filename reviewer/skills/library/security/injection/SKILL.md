---
name: injection
agent: security
description: Inyección en contextos que un análisis por reglas no sigue
applies_to: ["src/**"]
---
Sigue el flujo de los datos del usuario a través de varias funciones; Sonar suele detectar solo
el caso directo. Category `injection`:
- SQL: `query()` / `createQueryBuilder().where()` con strings construidos por interpolación o
  concatenación, aunque el valor pase por un helper intermedio. Lo seguro son los parámetros
  (`:id`, `?`).
- Ordenamiento o columnas dinámicas (`orderBy(req.query.sort)`) sin lista blanca.
- Rutas de archivo (`path.join`, `fs.*`) con datos del usuario sin normalizar ni confinar
  (path traversal, CWE-22).
- Comandos (`child_process`) o expresiones regulares construidas con datos del usuario (ReDoS).
- Headers o redirecciones con valores del usuario sin validar (open redirect).

Describe en `message` el camino del dato: dónde entra, por dónde pasa y dónde se usa.
