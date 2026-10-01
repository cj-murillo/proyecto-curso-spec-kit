# Data Model: CRUD completo de gastos y usuario

## Entidades

### Usuario (`usuarios`)

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | entero, PK | generado |
| `email` | texto, único, indexado | siempre en minúsculas (se normaliza en registro, login y cambio); formato de email válido |
| `hashed_password` | texto | hash Argon2; nunca se expone |

Relación: un usuario tiene 0..N gastos. **Baja**: al borrarse el usuario, la base elimina sus gastos (`ON DELETE CASCADE`).

Reglas de cambio:
- Cambiar email: exige `password_actual` correcta; el email nuevo no puede estar en uso (400); la unicidad final la garantiza el índice único (una carrera se traduce a 400).
- Cambiar contraseña: exige `password_actual` correcta y una nueva distinta (400); longitud 8-72 (422).
- Eliminar cuenta: exige `password_actual` correcta (400 si no).

### Gasto (`gastos`)

| Campo | Tipo | Reglas |
|---|---|---|
| `id` | entero, PK | generado; nunca viene del cliente |
| `descripcion` | texto | sin espacios en los extremos, 1-200 caracteres |
| `monto` | Float | `> 0`, `<= 1.000.000`, máximo 2 decimales |
| `categoria` | texto | una de `CATEGORIAS_PERMITIDAS` (`comida`, `transporte`, `entretenimiento`, `otros`) |
| `fecha` | fecha, NOT NULL | por defecto hoy; no puede ser futura; filas previas = fecha de la migración |
| `usuario_id` | entero, FK → `usuarios.id` `ON DELETE CASCADE`, indexado | solo del JWT; nunca del cliente |

Invariantes:
- Para cada usuario y categoría, `SUM(monto) <= 500` (acumulado histórico) en todo momento, incluso con peticiones simultáneas.
- Al editar, el total se calcula sin el gasto editado y para la categoría resultante.

### Credencial (JWT, no se almacena)

Claims: `sub` (email), `uid` (id del usuario), `exp`. Es válida solo si `sub` y `uid` apuntan al mismo usuario existente.

### Resumen de categoría (derivado, no se almacena)

`categoria`, `total` (suma en el rango), `cantidad` (en el rango), `disponible` = 500 − total **histórico** de la categoría. Siempre una fila por cada categoría permitida; más `total_general` (suma de los `total`).

## Transiciones de estado

- Gasto: `creado → (actualizado)* → eliminado`. Eliminado es terminal (consultarlo da 404).
- Usuario: `registrado → (email/contraseña cambiados)* → eliminado` (arrastra sus gastos).

## Migración (`alembic/versions/<rev>_gastos_fecha_cascade.py`, `down_revision = "7c1d2e9a4b30"`)

`upgrade()`:
1. `ADD COLUMN gastos.fecha DATE NOT NULL DEFAULT current_date` (rellena filas existentes).
2. Localizar con el inspector la FK `gastos.usuario_id → usuarios.id`, eliminarla y crear `fk_gastos_usuario_id` con `ondelete="CASCADE"`.
3. `CREATE INDEX ix_gastos_usuario_id`.
4. `UPDATE usuarios SET email = lower(email)` con SQLAlchemy Core.

`downgrade()`: eliminar índice, recrear la FK sin cascada, eliminar `fecha`. La normalización de emails no se revierte.

Verificación: `tests/test_migracion_gastos.py` (upgrade sobre filas existentes + downgrade) y `alembic check` sin diferencias.
