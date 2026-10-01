# Contrato MCP — feature 002

Todas las tools resuelven al usuario con la identidad del token verificado (Art. VI.4: `sub` + `uid` deben coincidir); sin token (stdio) usan el usuario demo documentado. Las fechas se devuelven en ISO 8601. Cualquier error de negocio, de inexistencia o de dueño se devuelve como `{"error": "mensaje"}`, nunca como excepción.

| Tool | Parámetros | Éxito | Notas |
|---|---|---|---|
| `registrar_gasto` (existente) | `descripcion`, `monto`, `categoria`, `fecha?` | gasto (dict con `fecha`) | Docstring corregido: el límite de 500 es acumulado por categoría |
| `listar_gastos` (existente) | `skip=0`, `limit=20`, `categoria?`, `desde?`, `hasta?`, `monto_min?`, `monto_max?`, `orden?` | lista de gastos | Sin filtros se comporta como en 001 |
| `obtener_gasto` | `gasto_id` | gasto | Inexistente o ajeno → `{"error"}` |
| `actualizar_gasto` | `gasto_id`, `descripcion?`, `monto?`, `categoria?`, `fecha?` (al menos uno) | gasto actualizado | Parcial; mismas reglas y límite que PATCH |
| `eliminar_gasto` | `gasto_id`, `confirmar=False` | `{"eliminado": true, "id": …}` | Sin `confirmar=True` no borra y devuelve `{"error": "Confirma la eliminación con confirmar=true"}` (Art. VI.5) |
| `resumen_gastos` | `desde?`, `hasta?` | igual a `ResumenGastos` | Siempre las 4 categorías |
| `listar_categorias` | — | `{"categorias": [...], "limite_por_categoria": 500}` | |

Cada tool tiene descripción específica y accionable (Art. VI.2) y ≥2 pruebas: un caso exitoso y uno de error de negocio (Art. VII.6).
