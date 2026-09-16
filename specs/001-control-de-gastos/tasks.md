# Tasks: Control de Gastos

**Input**: `plan.md`, `spec.md` en `specs/001-control-de-gastos/`

Convención: cada tarea de código es "done" solo con (1) código escrito, (2) test
correspondiente escrito y en verde, (3) sin violar ningún artículo de la constitución que
le aplica. Orden estricto por dirección de dependencia (Artículo I).

## Fase 0 — Andamiaje

- [x] **T001** `pyproject.toml` con las dependencias de `plan.md` (stack completo) +
  `[tool.coverage.run] omit` para `app/main.py`, `app/mcp/server.py`, `app/mcp/auth.py`,
  `app/logging_config.py`, + `[tool.coverage.report] fail_under = 80` (umbral mecánico del
  Artículo VII.3: sin esto, `pytest --cov` no falla aunque la cobertura baje). `uv sync`.
  - Artículo: VII.3. Sin test (config pura); verificado corriendo con
  `--cov-fail-under=99` a propósito y confirmando exit code 1.
- [x] **T002** `.env.example` con `SECRET_KEY`, `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
  `MCP_DEMO_EMAIL`, `MCP_DEMO_PASSWORD`, `MCP_ISSUER_URL`, `MCP_RESOURCE_URL` documentados
  sin valores reales. `.env` real generado con `openssl rand -hex 32` para `SECRET_KEY`,
  gitignored.
  - Artículo: IV.3. Sin test (config pura).
- [x] **T003** `app/config.py` — `Settings(BaseSettings)` leyendo `.env`.
  - Artículo: IV.3. Test: `tests/test_config.py::test_settings_carga_desde_env`.
- [x] **T004** `app/database.py` — `engine`, `Base`, `SessionLocal`, `get_db()`, con
  `connect_args` condicional a SQLite.
  - Artículo: III.1-2. Test: cubierto indirectamente por integración (T010).
- [x] **T005** `app/logging_config.py` — `configurar_logging(nivel)`.
  - Sin artículo de seguridad/negocio directo. Sin test (excluido de cobertura, T001).

## Fase 1 — Modelos

- [x] **T006** `app/models/usuario.py` — `Usuario(id, email unique, hashed_password)`.
  - Artículo: III.3. Test: implícito en T010 (integración).
- [x] **T007** `app/models/gasto.py` — `Gasto(id, descripcion, monto, categoria,
  usuario_id FK)`.
  - Artículo: III.3. Test: implícito en T010.
- [x] **T008** Migración Alembic inicial (`alembic revision --autogenerate` +
  `alembic upgrade head` verificado localmente).
  - Artículo: III.1. Checkpoint manual, no test automatizado.

## Fase 2 — Repositories (solo persistencia, Artículo VIII.2)

- [x] **T009** `app/repositories/usuarios.py` — `obtener_por_email(db, email)`,
  `guardar(db, email, hashed_password)`. Funciones sueltas, no clase.
  - Artículo: I.3, VIII.2. Test: cubierto por `test_integracion_gastos.py` (copiado en T020).
- [x] **T010** `app/repositories/gastos.py` — `guardar`, `listar`, `total_por_categoria`,
  firmas exactas del contrato de compatibilidad, devuelven `dict`.
  - Artículo: I.3, III.3, VIII.2. Test: `test_integracion_gastos.py` (copiado en T020).

## Fase 3 — Utils

- [x] **T011** `app/utils/validadores.py` — `CATEGORIAS_PERMITIDAS = {"comida",
  "transporte", "entretenimiento", "otros"}`, `categoria_valida(categoria)`.
  - Artículo: II.2 (OCP). Test: `tests/test_validadores.py::test_categoria_valida_e_invalida`.
- [x] **T012** `app/security.py` — `hash_password`, `verify_password`,
  `crear_access_token`, `decodificar_token` (HS256, `pyjwt`).
  - Artículo: IV.1-2. Test: `tests/test_security.py::test_hash_y_verify`,
  `test_security.py::test_token_expira`.

## Fase 4 — Services (lógica de negocio, DIP)

- [x] **T013** `app/services/gastos.py` — `CategoriaInvalidaError`, `LimiteExcedidoError`,
  `LIMITE_POR_CATEGORIA=500.0`, `_validar_gasto`, `registrar_gasto(db, usuario_id,
  descripcion, monto, categoria, repo=gastos_repository)`, `listar_gastos(db, usuario_id,
  skip=0, limit=20, repo=gastos_repository)`. Firmas exactas del contrato de compatibilidad.
  - Artículo: I.2, II.1, II.3, VIII.1. Test: `tests/test_gastos.py` (copiado en T020) — cubre
  los 3 casos de error de negocio (monto inválido, categoría inválida, límite excedido).
- [x] **T014** `app/services/usuarios.py` — `EmailYaRegistradoError`,
  `CredencialesInvalidasError`, `registrar_usuario`, `autenticar_usuario`.
  - Artículo: I.2, II.3. Test: `tests/test_usuarios_service.py::test_registrar_duplicado`,
  `test_usuarios_service.py::test_autenticar_credenciales_invalidas`.

## Fase 5 — Schemas

- [x] **T015** `app/schemas/gasto.py` — `GastoCreate`, `GastoResponse` (distintos,
  Artículo V.3).
  - Sin test directo, cubierto por tests de API (T020, T021).
- [x] **T016** `app/schemas/usuario.py` — `UsuarioCreate` (con `EmailStr`),
  `UsuarioResponse`.
  - Sin test directo, cubierto por tests de API.

## Fase 6 — Dependencies + Routers

- [x] **T017** `app/dependencies.py` — `get_current_user` (decodifica JWT, 401 si
  inválido), `get_gastos_repo`.
  - Artículo: IV.4. Test: cubierto por `test_api_gastos.py` vía `dependency_overrides`.
- [x] **T018** `app/routers/usuarios.py` — `POST /usuarios/`, `POST /usuarios/token`.
  - Artículo: V.1. Test: `tests/test_api_usuarios.py::test_registrar_y_login`,
  `test_api_usuarios.py::test_login_credenciales_invalidas_401`.
- [x] **T019** `app/routers/gastos.py` — `POST /gastos/`, `GET /gastos/`, `usuario_id`
  siempre desde `get_current_user`, excepciones de service → `400`, `skip`/`limit` con
  `Query(ge=..., le=...)` (Artículo V.2: negativos/inválidos → `422`).
  - Artículo: IV.4, V.1, V.2. Test: `test_api_gastos.py` (T020) cubre el caso exitoso y el
  500; `test_api_gastos.py::test_listar_gastos_con_paginacion_invalida_devuelve_422` cubre
  V.2. Los casos de error 4 y 5 del spec (401 sin token; `usuario_id` ajeno ignorado) —
  hallazgo del `/speckit-analyze` manual — se cubren en T020b. `GastoCreate` no declara
  campo `usuario_id`, así que un body con ese campo extra es ignorado por Pydantic; el test
  de T020b lo verifica explícitamente en vez de confiar en que "no está en el schema"
  demuestre por sí solo el comportamiento correcto.

## Fase 7 — Main + copiar tests de referencia

- [x] **T020** Copiar `tests/__init__.py`, `tests/test_gastos.py`,
  `tests/test_integracion_gastos.py`, `tests/test_api_gastos.py` desde
  `$RUTA_PROYECTO_S6_S8/tests/` (variable de entorno, ver Paso 8 de `practica_09.md` — la
  ruta real depende de dónde tenga cada quien su proyecto de S6-S8) — sin modificar
  aserciones (Artículo VIII.1).
  - Artículo: VIII.1. Correr y confirmar verde antes de continuar.
- [x] **T020b** `tests/test_autorizacion_gastos.py` (nuevo, no viene de S6-S8) — cubre los
  casos de error 4 y 5 de `spec.md` COMPLETOS (los dos verbos que menciona cada caso), que
  la suite copiada en T020 no cubre:
  - `test_listar_gastos_sin_token_devuelve_401`: cliente SIN override de
    `get_current_user` (usa el `oauth2_scheme` real) → `GET /gastos/` sin header
    `Authorization` → `401`.
  - `test_crear_gasto_sin_token_devuelve_401`: mismo patrón para `POST /gastos/` (spec.md
    dice "listar **o registrar** sin token").
  - `test_crear_gasto_ignora_usuario_id_del_body`: `POST /gastos/` con
    `{"descripcion": ..., "monto": ..., "categoria": ..., "usuario_id": 999}` autenticado
    como el usuario de prueba (id distinto de 999) → `201`, y el gasto queda asociado al
    `usuario_id` del token, nunca a `999` (verificar contra el repo falso inyectado).
  - `test_listar_gastos_ignora_usuario_id_del_query`: `GET /gastos/?usuario_id=999`
    autenticado como el usuario de prueba → `200`, filtrando siempre por el `usuario_id`
    del token (spec.md dice literalmente "**listar** gastos de otro usuario pasando su ID").
  - Artículo: IV.4, V.1 (casos de error 4 y 5 de `spec.md`, ambos verbos).
- [x] **T021** `app/main.py` — `FastAPI()`, `include_router`, middleware de logging,
  `@app.exception_handler(Exception)` → `500` + `{"detail": "Error interno del servidor"}`.
  - Artículo: IV.5. Test: `test_api_gastos.py::test_error_no_controlado_devuelve_500_sin_stacktrace`
  (ya cubierto por T020).

## Fase 8 — MCP

- [x] **T022** `app/mcp/auth.py` — `JWTTokenVerifier(TokenVerifier)` reutilizando
  `decodificar_token`.
  - Artículo: VI.4. Test: `tests/test_mcp_gastos.py::test_verifier_rechaza_token_invalido`.
- [x] **T023** `app/mcp/tools/gastos.py` — `registrar_gasto`, `listar_gastos(skip=0,
  limit=20)`. Resuelven usuario desde `get_access_token().subject` cuando hay token
  verificado; fallback a usuario demo de `.env` solo sin token, documentado con comentario
  (corrige el bug de identidad del proyecto de referencia — ver nota en `spec.md`). Ambas
  tools capturan `ValueError` y devuelven `{"error": ...}` (Artículo VI.3) — `listar_gastos`
  inicialmente solo tenía `try/finally` y dejaba escapar el error de identidad sin
  estructurar; corregido con el mismo patrón que ya tenía `registrar_gasto`.
  - Artículo: VI.1, VI.3, VI.4. Test: `tests/test_mcp_gastos.py::test_registrar_gasto_exitoso`,
  `test_mcp_gastos.py::test_registrar_gasto_categoria_invalida_retorna_error_estructurado`,
  `test_mcp_gastos.py::test_listar_gastos_token_sin_usuario_retorna_error_estructurado`
  (Artículo VII.6: ahora las dos tools tienen caso exitoso y caso de error de negocio).
- [x] **T024** `app/mcp/server.py` — monta `FastMCP` con `JWTTokenVerifier`, registra tools.
  - Artículo: VI. Montaje en `app/main.py` (`streamable_http_app()` bajo `/mcp`, lifespan
  que arranca `session_manager`). Sin test unitario directo (infraestructura, excluida de
  cobertura por T001); verificado con smoke manual (MCP Inspector u `httpx` contra `/mcp`).

## Fase 9 — Verificación final

- [x] **T025** Correr `pytest --cov=app --cov-report=term-missing -v` completo. Confirmar:
  - Los 3 archivos de tests copiados en T020 pasan sin modificar aserciones.
  - Los 5 casos de error de `spec.md` tienen cada uno un test identificable.
  - Cobertura `app/services/` ≥ 90%.
  - Cobertura del conjunto `services+repositories+routers+utils` ≥ 80%.
  - Si no se cumple: listar qué archivo/función quedó sin cubrir, agregar test, repetir —
  no se declara la tarea terminada con el umbral en rojo.
  - Artículo: VII.3, VII.7.

## Resultado de la verificación final (T025)

Corrida original (antes del cierre de brechas descrito abajo):

```
29 passed, 6 warnings in 6.06s
app/services/gastos.py     100%
app/services/usuarios.py   100%
app/repositories/gastos.py 100%
app/repositories/usuarios.py 100%
app/routers/gastos.py       89%
app/routers/usuarios.py    100%
app/utils/validadores.py   100%
TOTAL (app completo)        92%
```

Conjunto `services+repositories+routers+utils`: 98.3% (117 líneas, 2 sin cubrir en
`routers/gastos.py`, ninguna en camino de negocio). Cobertura de `services/` ≥90% cumplida
con margen. Smoke manual: `uvicorn` levanta, `/docs` y `/openapi.json` responden 200,
`/mcp/` exige auth (401 sin token), `/.well-known/oauth-protected-resource/mcp` responde
200, flujo REST completo (registro→login→crear gasto ignorando `usuario_id` ajeno→listar)
verificado con `curl`.

### Cierre de brechas post-auditoría

Una auditoría posterior contra `practica_09.md` encontró 3 desviaciones y 3 huecos de
cobertura de reglas, cerrados así:

- **Artículo V.2** (`app/routers/gastos.py`): `skip`/`limit` sin cota → `Query(ge=0)` /
  `Query(ge=1, le=100)`. Test: `test_api_gastos.py::test_listar_gastos_con_paginacion_invalida_devuelve_422`.
- **Artículo VI.3 / VII.6** (`app/mcp/tools/gastos.py`): `listar_gastos` sin `except` →
  ahora captura `ValueError` y devuelve `{"error": ...}`, igual que `registrar_gasto`. Test:
  `test_mcp_gastos.py::test_listar_gastos_token_sin_usuario_retorna_error_estructurado`.
- **Caso 4 de spec.md** (solo "registrar" faltaba): `test_autorizacion_gastos.py::test_crear_gasto_sin_token_devuelve_401`.
- **Caso 5 de spec.md** (solo "listar" faltaba, spec.md lo pide literalmente): `test_autorizacion_gastos.py::test_listar_gastos_ignora_usuario_id_del_query`.
- **Hueco de regla sin caso numerado**: paginación del service nunca se probó con un doble
  observando `skip`/`limit`. Test: `test_gastos_service_extra.py::test_listar_gastos_reenvia_paginacion_al_repositorio`.
- **Umbral mecánico** (Artículo VII.3): `pyproject.toml` ahora tiene
  `[tool.coverage.report] fail_under = 80`; verificado que `--cov-fail-under=99` sale con
  exit code 1.

Con estos 6 tests nuevos:

```
34 passed, 6 warnings in 4.54s
app/services/gastos.py      100%
app/repositories/gastos.py  100%
app/routers/gastos.py        94%
TOTAL (app completo)         92.4%
Required test coverage of 80.0% reached.
```

Los 5 casos de error de `spec.md` quedan cubiertos en ambos verbos donde el caso los
menciona: 1-3 en `test_gastos.py` (copiado, S6-S8); 4 (401) en
`test_autorizacion_gastos.py::test_listar_gastos_sin_token_devuelve_401` y
`::test_crear_gasto_sin_token_devuelve_401`; 5 (usuario_id ajeno ignorado) en
`::test_crear_gasto_ignora_usuario_id_del_body` y `::test_listar_gastos_ignora_usuario_id_del_query`.

## Dependencias entre tareas

```
T001,T002 → T003 → T004 → T006,T007 → T008
T004,T006,T007 → T009,T010
T011,T012 (independientes, después de T001)
T009,T010,T011,T012 → T013,T014
T013,T014 → T015,T016 → T017 → T018,T019
T018,T019 → T020 → T021
T012 → T022 → T023 → T024
T021,T024 → T025
```
