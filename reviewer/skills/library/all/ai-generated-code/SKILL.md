---
name: ai-generated-code
agent: all
description: Patrones de error típicos del código escrito por una IA
---
La mayoría de los PRs que revisas fueron escritos por una IA. Ese código suele verse correcto y
aun así fallar de formas previsibles. Verifica contra el código real; no confíes en comentarios,
nombres de funciones ni en la descripción del PR.

Presta especial atención a:
- APIs, métodos, opciones de configuración o paquetes que no existen (inventados).
- Casos borde sin manejar: `null`/`undefined`, listas vacías, duplicados, errores de la base de datos.
- Cambios más amplios que lo pedido (refactors, renombres o "mejoras" no solicitadas).
- Lógica que duplica algo que el repo ya resuelve en otro lugar.
- Tests que verifican el mock en lugar del comportamiento, o que se modificaron para que pasen.
- Comentarios o descripciones que afirman cosas que el código no hace.
