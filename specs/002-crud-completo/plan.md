# Implementation Plan: CRUD completo de gastos y usuario

**Branch**: `002-crud-completo` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-crud-completo/spec.md`

## Summary

Se completa la API de gastos (consulta, PUT, PATCH, DELETE, filtros, orden, resumen, categorías, fecha) y de usuario (`/me`, cambio de email y contraseña, baja de cuenta), se agregan las tools MCP equivalentes y `/health`. Todo es **aditivo** sobre la spec 001 (Art. VIII).

Enfoque técnico (detalle y alternativas en [research.md](./research.md)):

- **Una sola ruta de actualización**: `actualizar_gasto` sirve a PUT y PATCH; mezcla el gasto actual con los cambios, revalida el resultado completo y evalúa el límite de 500 excluyendo el propio gasto y sobre la categoría resultante.
- **Límite seguro bajo concurrencia**: las operaciones que cambian totales (`registrar_gasto`, `actualizar_gasto`) toman primero un bloqueo de fila sobre el usuario (`SELECT … FOR UPDATE`, vía SQLAlchemy) en el repository; la comprobación del total y la escritura quedan en la misma transacción.
- **Dueño verificado en el service**: `obtener_por_id` lee por `id`; el service decide 404 (no existe) o 403 (otro dueño) antes de exponer o tocar nada; escrituras y borrados además filtran por `usuario_id`.
- **Credencial con `uid`**: el JWT agrega el id del usuario; `get_current_user` y el verificador MCP exigen que `sub` (email) y `uid` coincidan con el mismo usuario. Tokens sin `uid` dejan de valer.
- **Validación en dos puertas**: schemas Pydantic (`extra="forbid"`, tipos reutilizables) y reglas de negocio en el service (MCP no pasa por schemas).
- **Una migración** de Alembic: `fecha`, FK con `ON DELETE CASCADE`, índice por `usuario_id` y emails en minúsculas; con `downgrade` real.

## Technical Context

**Language/Version**: Python 3.12 (`.python-version`, `requires-python = ">=3.12,<3.13"`)

**Primary Dependencies**: FastAPI 0.142, Pydantic 2.13, SQLAlchemy 2.1, Alembic 1.20, psycopg 3, pwdlib (Argon2), PyJWT 2.15, MCP SDK 2.2 (`MCPServer`). Sin dependencias nuevas.

**Storage**: PostgreSQL 16 (contenedor `postgres16`); bases `gastos` y `gastos_test`.

**Testing**: pytest + pytest-cov, `httpx2` (TestClient), Postgres real para integración (`TEST_DATABASE_URL`); sin `unittest.mock` (Art. VII.2).

**Target Platform**: servicio ASGI en Linux (uvicorn).

**Project Type**: web-service (API REST + servidor MCP montado en la misma app).

**Performance Goals**: sin metas numéricas (CRUD interactivo de un usuario); listado y resumen resueltos en una consulta cada uno, apoyados en el índice por `usuario_id`.

**Constraints**: aditivo sobre 001 (firmas y rutas existentes intactas); `filterwarnings` con `error` para `DeprecationWarning` y `ResourceWarning`; cobertura ≥80% global y ≥90% en `services/`.

**Scale/Scope**: aplicación personal; decenas a miles de gastos por usuario.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Artículo | Evaluación | Estado |
|---|---|---|
| I (capas) | Routers solo traducen; reglas en `services/`; solo `repositories/` toca la base (incluye `select 1` de salud y el bloqueo de fila). Tools MCP llaman a `services/`. | Cumple |
| II.1-II.3 (SRP/OCP/DIP) | `_validar_*` separado de la orquestación; el Enum de categorías se genera de `CATEGORIAS_PERMITIDAS`; todo service recibe `repo=`. | Cumple |
| III.1-III.2 | Solo SQLAlchemy Core/ORM, sin SQL concatenado; sin dependencia del motor salvo `FOR UPDATE` (estándar en SQLAlchemy). | Cumple |
| III.3 (filtro por `usuario_id`) | `obtener_por_id(db, gasto_id)` es la **única** lectura sin filtro de dueño: el service la necesita para distinguir 403 de 404 y compara el dueño antes de devolver nada. | **Enmienda aclaratoria** |
| IV.1-IV.3 | Sin cambios de hashing ni secretos; `.env.example` actualizado por el usuario. | Cumple |
| IV.4 (dueño) | `usuario_id` solo del JWT; verificación de dueño antes de leer/editar/borrar; `extra="forbid"` bloquea `usuario_id` en el body. | Cumple |
| IV.5 (500 genérico) | Se mantiene el handler global; `/health` devuelve 503 explícito. | Cumple |
| IV.6 | Schemas para toda entrada. | Cumple |
| V.1 (códigos) | PUT/PATCH → 200 y DELETE/acciones sin cuerpo → 204 no están listados; 403 se aplica a `{id}` ajeno como ya prevé. | **Enmienda** (FR-025) |
| V.2 (paginación) | `skip`/`limit` se mantienen, inválidos → 422. | Cumple |
| V.3 (schemas distintos) | `GastoCreate/Update/Patch` de entrada, `GastoResponse` de salida. | Cumple |
| VI.1-VI.4 | Tools llaman a services; errores como `{"error": …}`; identidad del token. | Cumple |
| VI.2 (descripciones) | El ejemplo de la constitución dice "límite mensual"; el límite es acumulado. | **Enmienda aclaratoria** |
| VI.5 (destructivas) | `eliminar_gasto(confirmar=False)` no borra sin `confirmar=True`. | Cumple |
| VII | Reglas con test unitario (repo falso), integración en Postgres, API con `dependency_overrides`, ≥2 tests por tool, prueba de concurrencia real. | Cumple |
| VIII (compatibilidad) | Ver "Compatibilidad con 001" abajo: firmas intactas y llamadas al repo con la forma legada cuando no se usan los parámetros nuevos. | Cumple |

**Resultado del gate**: aprobado con **3 enmiendas** a la constitución (V.1, III.3, VI.2), que se aplican en la fase Foundational, antes de escribir cualquier código que dependa de ellas, y suben la versión a 1.4.0. Sin violaciones que justificar (tabla de Complexity Tracking vacía).

**Re-evaluación post-diseño**: sin cambios; el bloqueo de fila y el claim `uid` no introducen violaciones.

## Compatibilidad con 001 (Art. VIII)

Los dobles de prueba copiados (`tests/test_gastos.py`, `test_api_gastos.py`, `test_autorizacion_gastos.py`) fijan las firmas `guardar(db, usuario_id, descripcion, monto, categoria)`, `listar(db, usuario_id, skip, limit)` y `total_por_categoria(db, usuario_id, categoria)`. Reglas de diseño para no romperlos:

1. Los parámetros nuevos de repository (`fecha`, filtros, orden, `excluir_id`) son opcionales **al final** y el service **solo los envía cuando tienen valor**; sin ellos llama con la forma de 001.
2. El bloqueo se invoca con un helper del service tolerante: `getattr(repo, "bloquear_usuario", None)`; un repo sin esa función (doble legado) simplemente no bloquea. El repository real siempre la define.
3. `registrar_gasto(db, usuario_id, descripcion, monto, categoria, repo=…)` y `listar_gastos(db, usuario_id, skip=0, limit=20, repo=…)` conservan nombre y orden; los parámetros nuevos entran como keywords después.
4. Los dicts del repository ganan la clave `fecha` (aditivo). `GastoResponse.fecha` es `date | None = None` solo para tolerar dobles legados cuyos dicts no la traen; el repository real siempre la devuelve.
5. `contar_gastos` devuelve `None` si el repo no define `contar` (dobles de 001) y el router omite `X-Total-Count`; así `test_listar_gastos_ignora_usuario_id_del_query` (que exige que el repo reciba una sola llamada) sigue pasando.
6. Los query params desconocidos del listado se ignoran (`FiltrosGastos` sin `extra="forbid"`): el caso de error 5 de 001 pide ignorar un `usuario_id` ajeno en el query. `extra="forbid"` aplica solo a cuerpos.

## Project Structure

### Documentation (this feature)

```text
specs/002-crud-completo/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, reglas, migración
├── quickstart.md        # Fase 1: guía de validación de punta a punta
├── contracts/
│   ├── rest-api.md      # Contrato REST (rutas, cuerpos, códigos)
│   └── mcp-tools.md     # Contrato de tools MCP
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks — NO lo crea /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── main.py                       # incluye router de health
├── database.py / config.py / security.py
├── dependencies.py               # get_current_user verifica uid
├── models/{gasto,usuario}.py     # Gasto.fecha, FK CASCADE, índice
├── schemas/{gasto,usuario}.py    # tipos reutilizables, Update/Patch/Filtros/PasswordChange…
├── repositories/{gastos,usuarios,salud}.py
├── services/{gastos,usuarios,salud}.py
├── routers/{gastos,usuarios,health}.py
├── utils/validadores.py          # CATEGORIAS_PERMITIDAS (fuente única)
└── mcp/{auth.py,server.py,tools/gastos.py}
alembic/versions/<rev>_gastos_fecha_cascade.py
tests/
├── conftest.py
├── test_*.py (existentes, ajustados solo donde cambia el token/uid)
├── test_gastos_crud_service.py   # unit con repo falso
├── test_gastos_integracion_crud.py, test_concurrencia_limite.py  # Postgres real
├── test_api_gastos_crud.py, test_api_usuarios_me.py, test_health.py
├── test_mcp_gastos_crud.py
└── test_migracion_gastos.py
.specify/memory/constitution.md   # v1.4.0 (enmiendas V.1, III.3, VI.2)
```

**Structure Decision**: se conserva la estructura en capas existente (proyecto único); solo se agregan módulos `salud` y `health` y archivos de prueba. No se crean carpetas nuevas en `app/`.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
