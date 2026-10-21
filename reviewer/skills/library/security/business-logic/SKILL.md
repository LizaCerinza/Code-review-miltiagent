---
name: business-logic
agent: security
description: Condiciones de carrera y reglas de negocio eludibles
applies_to: ["src/**/application/**", "src/**/*.use-case.ts", "src/**/*.service.ts", "src/**/*.repository.ts", "src/**/persistence/**"]
---
Busca lógica de negocio explotable:
- **Verificar y luego actuar (CWE-367)**: se comprueba que algo no existe (o que hay saldo, cupo,
  estado válido) y luego se escribe, sin restricción única en la base de datos ni transacción.
  Dos peticiones simultáneas pueden pasar la verificación. Category `race-condition`. Si existe una
  restricción única que lo respalda y el error se traduce bien, no es un hallazgo.
- Validaciones que solo existen del lado del cliente o en un endpoint, pero no en el caso de uso
  que comparten varios endpoints.
- Reglas de negocio que se pueden saltar cambiando el orden de las llamadas o enviando campos
  opcionales. Category `business-logic`.
