---
name: constitution-check
description: Usa esta skill al finalizar cualquier tarea de tasks.md, para verificar cumplimiento con la constitución antes de marcarla como terminada.
---
Verifica, en este orden: (1) capas respetadas, (2) DIP con parámetro por
defecto, (3) si toca datos de usuario, filtro por usuario_id desde JWT,
(4) test correspondiente en verde, (5) si toca MCP, reutiliza services/.
