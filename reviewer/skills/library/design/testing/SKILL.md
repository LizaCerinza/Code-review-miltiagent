---
name: testing
agent: design
description: Pruebas en la capa adecuada (Vitest, supertest)
applies_to: ["src/**", "test/**"]
---
Revisa cómo se prueba el código nuevo (category `testing`):
- Casos de uso nuevos o modificados sin test unitario. En el repo se prueban sin NestJS, con un
  repositorio en memoria que implementa el puerto.
- Endpoints nuevos sin test del controller o sin cobertura e2e del flujo.
- Tests que verifican detalles internos (que se llamó a un método del mock) en lugar del
  comportamiento observable (resultado, error lanzado, código HTTP).
- Tests que levantan toda la aplicación para probar lógica que vive en un caso de uso.
- Lógica compleja en los propios tests (condicionales, bucles) que los vuelve difíciles de leer.
