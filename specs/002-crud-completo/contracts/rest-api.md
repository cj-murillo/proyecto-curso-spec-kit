# Contrato REST — feature 002

Autenticación: `Authorization: Bearer <JWT>` (claims `sub` + `uid`) salvo donde se indica. Los cuerpos de `PUT`/`PATCH` y los de `/usuarios/me*` rechazan campos desconocidos (422); `POST /gastos/` los ignora (contrato 001). Descripción vacía, monto ≤ 0 y categoría inválida son reglas de negocio: 400 (contrato 001); límites de longitud/decimales/máximo y fecha futura son de schema: 422. Errores de regla de negocio: `400 {"detail": "..."}`. Error no controlado: `500 {"detail": "Error interno del servidor"}`.

## Gastos (`/gastos`)

Las rutas fijas `/resumen` y `/categorias` se declaran **antes** de `/{gasto_id}`.

| Método | Ruta | Auth | Request | Éxito | Errores |
|---|---|---|---|---|---|
| POST | `/gastos/` | sí | `GastoCreate`: `descripcion`, `monto`, `categoria`, `fecha?` | 201 `GastoResponse` | 400 (límite), 401, 422 |
| GET | `/gastos/` | sí | query: `skip`, `limit`, `categoria?`, `desde?`, `hasta?`, `monto_min?`, `monto_max?`, `orden?` | 200 `[GastoResponse]` + header `X-Total-Count` | 401, 422 |
| GET | `/gastos/resumen` | sí | query: `desde?`, `hasta?` | 200 `ResumenGastos` | 401, 422 |
| GET | `/gastos/categorias` | sí | — | 200 `{"categorias": [...], "limite_por_categoria": 500}` | 401 |
| GET | `/gastos/{gasto_id}` | sí | — | 200 `GastoResponse` | 401, 403, 404 |
| PUT | `/gastos/{gasto_id}` | sí | `GastoUpdate`: los 4 campos obligatorios | 200 `GastoResponse` | 400 (límite), 401, 403, 404, 422 |
| PATCH | `/gastos/{gasto_id}` | sí | `GastoPatch`: ≥1 campo, ninguno `null` | 200 `GastoResponse` | 400, 401, 403, 404, 422 |
| DELETE | `/gastos/{gasto_id}` | sí | — | 204 | 401, 403, 404 |

`GastoResponse`: `{ "id": int, "descripcion": str, "monto": float, "categoria": str, "fecha": "YYYY-MM-DD" }`.

`orden` ∈ {`fecha`, `-fecha`, `monto`, `-monto`}; por omisión y como desempate, `id` ascendente. `desde > hasta` o `monto_min > monto_max` → 422.

`ResumenGastos`:
```json
{
  "categorias": [
    {"categoria": "comida", "total": 120.0, "cantidad": 3, "disponible": 380.0},
    {"categoria": "entretenimiento", "total": 0.0, "cantidad": 0, "disponible": 500.0},
    {"categoria": "otros", "total": 0.0, "cantidad": 0, "disponible": 500.0},
    {"categoria": "transporte", "total": 30.0, "cantidad": 1, "disponible": 470.0}
  ],
  "total_general": 150.0
}
```
`total`/`cantidad` respetan `desde`/`hasta`; `disponible` = 500 − total histórico de la categoría.

## Usuarios (`/usuarios`)

| Método | Ruta | Auth | Request | Éxito | Errores |
|---|---|---|---|---|---|
| POST | `/usuarios/` | no | `UsuarioCreate`: `email` (minúsculas), `password` 8-72 | 201 `UsuarioResponse` | 400 (email duplicado), 422 |
| POST | `/usuarios/token` | no | form OAuth2 (`username`, `password`) | 200 `{access_token, token_type}` (token con `uid`) | 401 |
| GET | `/usuarios/me` | sí | — | 200 `UsuarioResponse` `{id, email}` | 401 |
| PATCH | `/usuarios/me` | sí | `{"email", "password_actual"}` | 200 `{id, email, access_token, token_type}` | 400 (email en uso / contraseña incorrecta), 401, 422 |
| PUT | `/usuarios/me/password` | sí | `{"password_actual", "password_nueva"}` (nueva 8-72) | 204 | 400 (actual incorrecta / nueva igual), 401, 422 |
| DELETE | `/usuarios/me` | sí | `{"password_actual"}` (cuerpo JSON) | 204 | 400 (contraseña incorrecta), 401, 422 |

Un token sin `uid`, con `uid` distinto del usuario resuelto por `sub`, o de un usuario inexistente → 401.

## Operación

| Método | Ruta | Auth | Éxito | Errores |
|---|---|---|---|---|
| GET | `/health` | no | 200 `{"status": "ok", "db": "ok"}` | 503 `{"status": "degraded", "db": "error"}` |

## Compatibilidad con 001

`POST /usuarios/`, `POST /usuarios/token`, `POST /gastos/` y `GET /gastos/` conservan ruta, método y comportamiento; solo ganan campos opcionales (`fecha`, filtros, `X-Total-Count`) y `fecha` en la respuesta.
