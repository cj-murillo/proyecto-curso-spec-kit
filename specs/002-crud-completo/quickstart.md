# Quickstart: validar la feature 002 de punta a punta

Contratos: [rest-api.md](./contracts/rest-api.md) · [mcp-tools.md](./contracts/mcp-tools.md) · modelo: [data-model.md](./data-model.md).

## Prerrequisitos

- Contenedor `postgres16` en marcha, con las bases `gastos` y `gastos_test`.
- `.env` con `SECRET_KEY` (≥32 caracteres), `DATABASE_URL` y `TEST_DATABASE_URL` (esta última termina en `_test` y es distinta de `DATABASE_URL`).
- `uv sync` hecho (Python 3.12).

## 1. Pruebas automáticas

```bash
uv run pytest --cov --cov-report=term-missing
```

Esperado: todo en verde, 0 warnings, cobertura ≥80% global y ≥90% en `services/`.

## 2. Migración sobre datos existentes

```bash
uv run alembic upgrade head
uv run alembic check          # "No new upgrade operations detected."
```

Esperado: gastos previos conservados con `fecha` = fecha de la migración. `tests/test_migracion_gastos.py` lo comprueba con filas y también el `downgrade`.

## 3. Recorrido manual (REST)

```bash
uv run uvicorn app.main:app --port 8000
```

1. `POST /usuarios/` (password ≥8) y `POST /usuarios/token` → copiar `access_token`.
2. `POST /gastos/` sin `fecha` → 201 con `fecha` de hoy; con fecha futura → 422.
3. `GET /gastos/{id}` → 200. `PUT` completo → 200; `PUT` sin un campo → 422; `PATCH {}` → 422; `PATCH {"monto": …}` → 200.
4. Subir `comida` hasta 450 y editar un gasto para pasar de 500 → 400; mover otro desde `transporte` → 400.
5. `GET /gastos/?categoria=comida&orden=-monto&desde=…&hasta=…` → lista filtrada; header `X-Total-Count`. `desde > hasta` → 422.
6. `GET /gastos/resumen` → 4 categorías (las vacías con 0/0/500) y `total_general`.
7. Segundo usuario: `GET/PUT/PATCH/DELETE` sobre el gasto del primero → 403; `id` inexistente → 404.
8. `DELETE /gastos/{id}` → 204; luego `GET` → 404.
9. `GET /usuarios/me` → 200. `PATCH /usuarios/me` con contraseña incorrecta → 400; correcta → 200 con token nuevo; el token anterior → 401.
10. `PUT /usuarios/me/password` → 204; login con la nueva funciona.
11. `DELETE /usuarios/me` con contraseña incorrecta → 400; correcta → 204; sus gastos desaparecen; su token → 401.
12. `GET /health` → 200; con la base detenida → 503.

## 4. Recorrido MCP

Con un Bearer válido sobre `/mcp/`: `initialize` y `tools/list` muestran las 7 tools. `eliminar_gasto` sin `confirmar` devuelve `{"error": …}` y no borra; con `confirmar=true` elimina.

## 5. Concurrencia del límite

```bash
uv run pytest tests/test_concurrencia_limite.py -q
```

Esperado: con 400 acumulados, dos gastos simultáneos de 60 → exactamente un 201 y un 400; total 460.

## 6. Limpieza

Vaciar las tablas de `gastos` si se usó la base de desarrollo: `TRUNCATE gastos, usuarios RESTART IDENTITY CASCADE`.
