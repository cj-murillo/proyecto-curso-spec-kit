---
name: mcp-tool-check
description: Usa esta skill después de escribir o modificar cualquier tool en app/mcp/tools/, antes de darla por terminada.
---
Verifica, en este orden: (1) la tool llama a una función de services/, no
reimplementa la regla adentro (Artículo VI.1); (2) la descripción de la tool
es específica y accionable, no genérica (Artículo VI.2); (3) un error de
negocio se devuelve como {"error": "..."}, nunca como excepción sin
controlar (Artículo VI.3); (4) la identidad del usuario sale del token
verificado cuando lo hay, el usuario demo es solo el fallback documentado
para stdio sin token (Artículo VI.4); (5) existen al menos dos tests para
la tool: un caso exitoso y un caso de error de negocio (Artículo VII.6).
