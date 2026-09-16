# Implementation Plan: Control de Gastos

**Branch**: `001-control-de-gastos` | **Date**: 2026-09-14 | **Spec**: `spec.md`

**Input**: Feature specification from `specs/001-control-de-gastos/spec.md`

## Summary

API REST de control de gastos personales con autenticación OAuth2+JWT, persistencia
SQLAlchemy+Alembic, y un servidor MCP (`streamable-http`) que expone `registrar_gasto` y
`listar_gastos` reutilizando la misma capa de `services/` que el router REST.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`,
`pyjwt`, `passlib[bcrypt]`, `bcrypt<4.1`, `pydantic-settings`, `email-validator`,
`python-multipart`, `mcp[cli]<2`

**Storage**: SQLite en desarrollo (`sqlite:///./gastos.db`); `database.py` no debe requerir
cambios para apuntar a Postgres (Artículo III.2).

**Testing**: `pytest`, `pytest-cov`, `httpx` (para `TestClient`)

**Target Platform**: Linux, servidor ASGI (uvicorn)

**Project Type**: API backend single-module (`app/`)

## Stack completo y por qué (no dos opciones — una decisión)

```
fastapi              → framework HTTP, valida con Pydantic (Artículo IV.6)
uvicorn[standard]     → servidor ASGI de desarrollo
sqlalchemy>=2         → ORM (Artículo III.1)
alembic               → migraciones (Artículo III.1)
pyjwt                 → JWT HS256 (Artículo IV.2) — única librería de JWT, no se ofrece
                        alternativa (python-jose): un plan que da a elegir reintroduce la
                        ambigüedad que la constitución existe para eliminar
passlib[bcrypt]       → hashing (Artículo IV.1)
bcrypt<4.1            → passlib 1.7.4 rompe en runtime con bcrypt>=4.1 (backend `__about__`
                        removido) — pin necesario, no cosmético
pydantic-settings     → Settings desde .env (Artículo IV.3)
email-validator       → requerido por `pydantic.EmailStr` en schemas/usuario.py
python-multipart      → requerido por `OAuth2PasswordRequestForm` en /usuarios/token
mcp[cli]<2            → SDK oficial de MCP, montado como streamable-http (Artículo VI)
pytest, pytest-cov    → testing y cobertura (Artículo VII.3)
httpx                 → dependencia de fastapi.testclient.TestClient
```

## Trazabilidad plan → constitución

- **Artículo I** (capas): paquetes Python separados bajo `app/` —
  `routers/`, `services/`, `repositories/`, `utils/`, `models/`, `schemas/`, `mcp/` — sin
  imports cruzados que violen la dirección de dependencia (`routers` → `services` →
  `repositories` → `models`; nunca al revés).
- **Artículo II.3** (DIP): parámetros por defecto en las funciones de `services/`
  (`repo=gastos_repository`), no un contenedor de inyección de dependencias externo.
- **Artículo III**: `sqlalchemy.create_engine` con `connect_args={"check_same_thread": False}`
  solo activo cuando `DATABASE_URL` empieza con `sqlite://`; el resto del código no conoce
  el motor concreto.
- **Artículo IV** (seguridad): `pyjwt` para JWT, `passlib.context.CryptContext(schemes=["bcrypt"])`
  para hashing, `pydantic_settings.BaseSettings` leyendo `.env` para `SECRET_KEY` y
  `DATABASE_URL`. Handler global `@app.exception_handler(Exception)` en `main.py` para el
  Artículo IV.5.
- **Artículo IV.4 / V.1** (autorización): toda ruta y tool que opera sobre gastos depende de
  `get_current_user` (REST) o del token verificado por MCP para obtener `usuario_id`; ningún
  endpoint ni tool acepta `usuario_id` como parámetro de entrada. No hay endpoint que reciba
  un gasto por `id` de otro usuario en este alcance (spec no incluye editar/eliminar), así
  que el camino de "403 sobre recurso ajeno" del Artículo V.1 queda sin uso hasta que se
  agregue esa operación — se documenta como alcance no cubierto, no como omisión.
- **Artículo V**: `GastoCreate`/`GastoResponse`, `UsuarioCreate`/`UsuarioResponse` como
  schemas Pydantic separados del modelo SQLAlchemy (Artículo V.3). `skip`/`limit` con
  default `0`/`20` (Artículo V.2), tipados `int` en la firma del router para que un valor
  no numérico dispare `422` automáticamente vía FastAPI/Pydantic.
- **Artículo VI** (MCP): montado dentro de la misma app FastAPI (`streamable_http_app()`
  montado en `/mcp`), reutilizando `app/services/gastos.py` desde `app/mcp/tools/gastos.py`.
  `JWTTokenVerifier` decodifica el mismo JWT que REST; la tool resuelve el usuario desde
  `get_access_token().subject` cuando hay token verificado (Artículo VI.4), y solo cae al
  usuario demo de `.env` cuando no hay ningún token (documentado con comentario explícito).
- **Artículo VII** (testing): fixtures de pytest para DB en memoria
  (`sqlite:///:memory:`), `app.dependency_overrides` para tests de API, `pytest-cov` con
  `--cov=app` y un `[tool.coverage.run] omit` explícito para `app/main.py`,
  `app/mcp/server.py`, `app/mcp/auth.py`, `app/logging_config.py` — infraestructura de
  arranque sin lógica de negocio, excluida a propósito (Artículo VII.3), verificado como
  último paso de `/speckit-implement`, no como tarea opcional.
- **Artículo VIII** (compatibilidad): firmas de `services/gastos.py` y `repositories/`
  copiadas literalmente de la sección "Contrato de compatibilidad" de `spec.md`.

## Estructura de proyecto

```
app/
├── config.py              # Settings (Artículo IV.3)
├── database.py             # engine, Base, get_db, SessionLocal (Artículo III)
├── security.py             # hash/verify password, JWT (Artículo IV.1-2)
├── dependencies.py         # get_current_user, get_gastos_repo (Artículo IV.4)
├── logging_config.py
├── main.py                  # FastAPI app, exception handler, mount MCP
├── models/
│   ├── usuario.py
│   └── gasto.py
├── schemas/
│   ├── usuario.py
│   └── gasto.py
├── repositories/
│   ├── usuarios.py
│   └── gastos.py            # módulo con funciones, no clase (Artículo VIII.2)
├── services/
│   ├── usuarios.py
│   └── gastos.py             # reglas de negocio + excepciones propias
├── routers/
│   ├── usuarios.py
│   └── gastos.py
└── mcp/
    ├── server.py
    ├── auth.py               # JWTTokenVerifier
    └── tools/
        └── gastos.py

alembic/                      # migraciones (Artículo III.1)
tests/
├── __init__.py
├── test_gastos.py                    # copiado de S6-S8, sin modificar
├── test_integracion_gastos.py        # copiado de S6-S8, sin modificar
├── test_api_gastos.py                # copiado de S6-S8, sin modificar
└── test_mcp_gastos.py                # nuevo, Artículo VII.6
```
