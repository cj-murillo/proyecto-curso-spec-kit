---

description: "Lista de tareas para la feature 002: CRUD completo de gastos y usuario"
---

# Tasks: CRUD completo de gastos y usuario

**Input**: Documentos de diseño en `/specs/002-crud-completo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/rest-api.md, contracts/mcp-tools.md, quickstart.md

**Tests**: INCLUIDOS. La constitución (Art. VII.2, VII.4-VII.7) y la spec (SC-007) los exigen: cada regla con test unitario (repo falso, sin `unittest.mock`), integración en Postgres real, API con `dependency_overrides`, ≥2 tests por tool MCP, y ninguna tarea cuenta como terminada sin su test en verde.

**Organization**: Tareas agrupadas por historia de usuario. Excepción de orden: **US4 (fecha, P2) se implementa antes que US1** porque toda respuesta de gasto incluye `fecha` (dependencia técnica, no de prioridad).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US7)
- Todas las rutas son relativas a la raíz del repo

## Reglas transversales (aplican a todas las tareas)

- **Compatibilidad con 001 (Art. VIII)**: las firmas existentes no cambian; los parámetros nuevos de repository/service son opcionales al final y el service **solo los envía cuando tienen valor** (los dobles de `tests/test_gastos.py`, `test_api_gastos.py` y `test_autorizacion_gastos.py` fijan `guardar(db, usuario_id, descripcion, monto, categoria)`, `listar(db, usuario_id, skip, limit)` y `total_por_categoria(db, usuario_id, categoria)`).
- **Entorno de pruebas**: exportar `SECRET_KEY`, `DATABASE_URL` y `TEST_DATABASE_URL` (termina en `_test`) antes de `uv run pytest`.
- **Cierre de cada fase**: `uv run pytest -q` en verde, sin warnings.

---

## Phase 1: Setup

- [X] T001 Verificar la línea base antes de tocar código: con las variables de entorno exportadas, correr `uv run pytest -q --cov` y confirmar que los 41 tests actuales pasan con 0 warnings (sin cambios de archivos).

---

## Phase 2: Foundational (bloquea todas las historias)

**Purpose**: esquema de base de datos, credencial con `uid` y fixtures compartidos.

- [X] T002 Actualizar `app/models/gasto.py`: agregar `fecha: Mapped[date] = mapped_column(default=date.today, server_default=func.current_date())` (NOT NULL), `usuario_id` con `ForeignKey("usuarios.id", ondelete="CASCADE")` e `index=True`.
- [X] T003 Crear la migración `alembic/versions/<rev>_gastos_fecha_cascade.py` con `down_revision = "7c1d2e9a4b30"`. `upgrade()`: (1) `add_column("gastos", Column("fecha", Date, nullable=False, server_default=func.current_date()))`; (2) localizar con `sa.inspect(op.get_bind()).get_foreign_keys("gastos")` la FK hacia `usuarios`, `drop_constraint` y `create_foreign_key("fk_gastos_usuario_id", "gastos", "usuarios", ["usuario_id"], ["id"], ondelete="CASCADE")`; (3) `create_index("ix_gastos_usuario_id", "gastos", ["usuario_id"])`; (4) normalizar `usuarios.email` con `update().values(email=func.lower(...))` en SQLAlchemy Core (sin SQL crudo). `downgrade()` real: `drop_index`, `drop_constraint("fk_gastos_usuario_id")`, recrear la FK sin cascada, `drop_column("fecha")`; la normalización de emails no se revierte (docstring). (depende de T002)
- [X] T004 [P] Crear `tests/test_migracion_gastos.py` contra `gastos_test` (patrón de `tests/test_migracion_hashes.py`, con `cfg.attributes["database_url"]` y limpieza en `finally`): upgrade a `7c1d2e9a4b30`, insertar usuario (email `Mayus@Ejemplo.com`) y un gasto, `command.upgrade(cfg, "head")`; comprobar que el gasto sigue, que `fecha` = fecha de hoy, que el email quedó en minúsculas, que borrar el usuario borra su gasto (`ON DELETE CASCADE`), y que `command.downgrade(cfg, "7c1d2e9a4b30")` quita `fecha` sin perder filas. (depende de T003)
- [X] T005 Emitir y verificar la credencial con `uid` (FR-018, FR-019): en `app/routers/usuarios.py::login` usar `crear_access_token({"sub": usuario.email, "uid": usuario.id})`; en `app/dependencies.py::get_current_user` exigir `payload.get("uid") == usuario.id` además de resolver por `sub` (sin `uid` o con otro `uid` → mismo 401 `credenciales_exception`).
- [X] T006 [P] Verificar `uid` en MCP (FR-018): en `app/mcp/auth.py::JWTTokenVerifier.verify_token` devolver `AccessToken(..., claims={"uid": payload.get("uid")})`; en `app/mcp/tools/gastos.py::_resolver_usuario_actual` rechazar con `ValueError("El token no corresponde a ningún usuario registrado")` si `access_token.claims.get("uid") != usuario.id` o falta.
- [X] T007 Mover el fixture `client` de `tests/test_api_usuarios.py` a `tests/conftest.py` (mismo comportamiento: `TestClient(app, raise_server_exceptions=False)` con `app.dependency_overrides[get_db]` sobre `SessionLocalDePrueba`, y `dependency_overrides.clear()` al salir) y agregar el helper `registrar_y_loguear(client, email="a@ejemplo.com", password="clave12345") -> dict` que devuelve `{"Authorization": "Bearer …"}`. Actualizar `tests/test_api_usuarios.py` para usar el fixture compartido y contraseñas de ≥8 caracteres. (depende de T005)
- [X] T008 [P] Actualizar `tests/test_mcp_gastos.py`: el doble `_AccessTokenFalso` pasa a recibir `subject` y `claims={"uid": id}`; el token real de `JWTTokenVerifier` se crea con `crear_access_token({"sub": …, "uid": …})`. Agregar tests: token sin `uid` → verificador devuelve el `AccessToken` pero la tool responde `{"error": …}`; `uid` de otro usuario → `{"error": …}`. (depende de T006)
- [X] T009 [P] Agregar a `tests/test_api_usuarios.py` (o archivo propio `tests/test_credencial_uid.py`) tests de API con Postgres: token legado sin `uid` → 401; token con `sub` válido pero `uid` ajeno → 401; token válido → 200 en una ruta protegida existente (`GET /gastos/`). (depende de T005, T007)
- [X] T010 Enmendar `.specify/memory/constitution.md` a v1.4.0 (`Last Amended`: fecha de hoy): Art. V.1 agrega `PUT`/`PATCH` → `200` y `DELETE`/acciones sin cuerpo → `204`; Art. III.3 aclara que `obtener_por_id` es la única lectura sin filtro de dueño y existe para distinguir 403 de 404; Art. VI.2 reemplaza "límite mensual" por "límite acumulado por categoría". Debe quedar aplicada **antes** de implementar T022, T024 y T027: la Gobernanza exige que la desviación esté aprobada antes de codificarla.

**Checkpoint**: `alembic upgrade head` aplica; tests existentes en verde con la credencial nueva.

---

## Phase 3: User Story 4 - Fecha en cada gasto (Priority: P2, prerrequisito de US1) 

**Goal**: cada gasto tiene `fecha` (por defecto hoy, nunca futura); se valida en las dos puertas.

**Independent Test**: crear un gasto sin fecha → fecha de hoy; con fecha futura → 422; el service rechaza fecha futura con `ValueError`.

### Tests for User Story 4

- [X] T011 [P] [US4] Crear `tests/test_schemas_gasto.py` con una prueba por regla de FR-012: `descripcion` "sin espacios en los extremos, 1-200 caracteres" (`"  Almuerzo  "` → `"Almuerzo"`, `""`/solo espacios/201 caracteres → inválido); `monto` "`> 0`, `<= 1.000.000`, máximo 2 decimales" (0, −1, 12.345, 1_000_000.01 inválidos; 12.5 y 1_000_000 válidos); `categoria` solo las de `CATEGORIAS_PERMITIDAS`; `fecha` no futura; campos desconocidos (`usuario_id`, `id`) → error por `extra="forbid"`.
- [X] T012 [P] [US4] Crear `tests/test_gastos_fecha.py` (service con repo falso): `registrar_gasto` sin `fecha` llama a `repo.guardar` con la forma legada de 001 (sin `fecha`); con `fecha` pasada la envía; fecha futura → `ValueError` y `guardar` no se llama; fecha de hoy y pasada se aceptan.
- [X] T013 [P] [US4] Crear `tests/test_api_gastos_fecha.py` (API con repo falso y `dependency_overrides`): `POST /gastos/` sin fecha → 201 con `fecha` de hoy en la respuesta; con fecha futura → 422; con `usuario_id` en el body → 422.

### Implementation for User Story 4

- [X] T014 [US4] Reescribir `app/schemas/gasto.py` con tipos anotados reutilizables y `extra="forbid"`: `Descripcion` (strip, longitud 1-200), `Monto` (`gt=0`, `le=1_000_000`, validador `Decimal(str(v)).as_tuple().exponent >= -2`), `Categoria` (`Enum` generado desde `CATEGORIAS_PERMITIDAS` de `app/utils/validadores.py`), `FechaNoFutura` (`<= date.today()`); `GastoCreate` (campos obligatorios `descripcion`, `monto`, `categoria`; `fecha` opcional) y `GastoResponse` (con `fecha: date | None = None` —opcional solo para tolerar los dobles de 001 cuyos dicts no la traen; el repository real siempre la devuelve— y `from_attributes=True`). (depende de T002)
- [X] T015 [US4] Actualizar `app/repositories/gastos.py`: `guardar(db, usuario_id, descripcion, monto, categoria, fecha=None)` (si `fecha` es `None` usa el default del modelo) y agregar la clave `fecha` a todos los dicts devueltos por `guardar` y `listar`. (depende de T002)
- [X] T016 [US4] Actualizar `app/services/gastos.py`: errores `GastoNoEncontradoError` y `AccesoDenegadoError`; `_validar_fecha(fecha)` (lanza `ValueError("La fecha no puede ser futura")`); `_validar_gasto(descripcion, monto, categoria, fecha=None)`; `registrar_gasto(db, usuario_id, descripcion, monto, categoria, fecha=None, repo=gastos_repository)` enviando `fecha` a `repo.guardar` **solo si no es `None`**. (depende de T015)
- [X] T017 [US4] Actualizar `app/routers/gastos.py::crear` para pasar `datos.fecha` al service solo cuando venga informada y devolver `GastoResponse` con `fecha`. (depende de T014, T016)

**Checkpoint**: T011-T013 en verde; tests de 001 intactos.

---

## Phase 4: User Story 1 - Corregir o eliminar un gasto (Priority: P1) 🎯 MVP

**Goal**: consultar, reemplazar (PUT), modificar (PATCH) y eliminar un gasto propio; 404 si no existe, 403 si es ajeno.

**Independent Test**: crear gasto → `GET` → `PUT` → `PATCH` → `DELETE` → `GET` (404); con otro usuario → 403 sin cambios.

### Tests for User Story 1

- [X] T018 [P] [US1] Crear `tests/test_gastos_crud_service.py` (service con repo falso en memoria que implementa `obtener_por_id`, `actualizar`, `eliminar`): obtener propio/inexistente (`GastoNoEncontradoError`)/ajeno (`AccesoDenegadoError`, sin llamar `actualizar`/`eliminar`); `actualizar_gasto` con los 4 campos (PUT) y con un solo campo (PATCH, los demás intactos); `cambios` vacío → `ValueError`; resultado combinado inválido (monto ≤ 0, categoría inválida, fecha futura) → error y sin escritura; `eliminar_gasto` propio/ajeno/inexistente.
- [X] T019 [P] [US1] Crear `tests/test_api_gastos_crud.py` (API con repo falso y `dependency_overrides` de `get_db`, `get_gastos_repo`, `get_current_user`): `GET /gastos/{id}` 200/404/403; `PUT` completo 200 y sin un campo 422; `PATCH` parcial 200, `{}` 422, `{"monto": null}` 422; `DELETE` 204 y luego 404; cuerpo con `usuario_id` o `id` → 422 en PUT y PATCH.
- [X] T020 [P] [US1] Crear `tests/test_gastos_integracion_crud.py` (Postgres real, `SessionLocalDePrueba`): ciclo crear → obtener → PUT → PATCH → eliminar con el repo real; el usuario B no puede leer/modificar/eliminar el gasto de A y el gasto de A queda intacto; `actualizar`/`eliminar` del repository filtran por `usuario_id` (devuelven `None`/`False` para otro dueño).

### Implementation for User Story 1

- [X] T021 [US1] En `app/schemas/gasto.py` agregar `GastoUpdate` (obligatorios: `descripcion`, `monto`, `categoria`, `fecha`; mismos tipos de T014; `extra="forbid"`) y `GastoPatch` (todos opcionales, `extra="forbid"`, validador `model_validator(mode="after")` que exige al menos un campo en `model_fields_set` y rechaza `null` explícito). (depende de T014)
- [X] T022 [US1] En `app/repositories/gastos.py` agregar `obtener_por_id(db, gasto_id) -> dict | None` (incluye `usuario_id`; única lectura sin filtro de dueño, Art. III.3 enmendado), `actualizar(db, gasto_id, usuario_id, descripcion, monto, categoria, fecha) -> dict | None` y `eliminar(db, gasto_id, usuario_id) -> bool`, ambos con `WHERE id AND usuario_id`. (depende de T015)
- [X] T023 [US1] En `app/services/gastos.py` agregar `_cargar_gasto_propio(db, usuario_id, gasto_id, repo)` (404 → `GastoNoEncontradoError`; dueño distinto → `AccesoDenegadoError`), `obtener_gasto`, `actualizar_gasto(db, usuario_id, gasto_id, cambios: dict, repo=…)` (mezcla el gasto actual con `cambios`, exige ≥1 cambio, revalida con `_validar_gasto` el resultado completo y llama a `repo.actualizar`) y `eliminar_gasto`; todos con `repo=` inyectable (Art. II.3). La evaluación del límite se agrega en US2. (depende de T016, T022)
- [X] T024 [US1] En `app/routers/gastos.py` agregar `GET /{gasto_id}`, `PUT /{gasto_id}` (`GastoUpdate`), `PATCH /{gasto_id}` (`GastoPatch`, `model_dump(exclude_unset=True)`) y `DELETE /{gasto_id}` (204), con `get_current_user`, `get_db` y `get_gastos_repo`; mapear `GastoNoEncontradoError`→404, `AccesoDenegadoError`→403, `ValueError`/`CategoriaInvalidaError`/`LimiteExcedidoError`→400. Agregarlas al final del router; US3 (T035) insertará `/resumen` y `/categorias` **por encima** de `/{gasto_id}`. (depende de T021, T023)

**Checkpoint**: US1 funcional e independiente; MVP entregable.

---

## Phase 5: User Story 2 - Respetar el límite al editar (Priority: P1)

**Goal**: el límite de 500 (acumulado histórico) se cumple al crear, editar o mover, también con peticiones simultáneas.

**Independent Test**: con 400 en `comida`, editar a 450 pasa y a 550 falla; mover desde `transporte` falla; dos altas simultáneas de 60 → una sola entra.

### Tests for User Story 2

- [X] T025 [P] [US2] Crear `tests/test_gastos_limite_edicion.py` (service con repo falso con `total_por_categoria(..., excluir_id=None)` y `bloquear_usuario`): AC9 (400 con un gasto de 100 → 150 acepta, → 250 rechaza y el monto queda en 150); AC10 (mover 100 de `transporte` a `comida` con 450 → `LimiteExcedidoError`); guardar el mismo gasto sin cambios no se rechaza por contarse a sí mismo; el service llama a `bloquear_usuario` antes de leer el total en `registrar_gasto` y `actualizar_gasto`; con un repo sin `bloquear_usuario` (doble legado) sigue funcionando.
- [X] T026 [P] [US2] Crear `tests/test_concurrencia_limite.py` (Postgres real, `pg_engine`, **dos hilos** con sesiones propias y `threading.Barrier`): usuario con 400 en `comida`; dos `registrar_gasto` simultáneos de 60 → exactamente uno se acepta, el otro lanza `LimiteExcedidoError`, total final 460 (nunca 520). Repetir con una edición y un alta simultáneas. Cada hilo cierra su sesión en `finally` (libera el bloqueo aunque lance `LimiteExcedidoError`). Agregar el caso de dos ediciones simultáneas del **mismo** gasto: ninguna falla por concurrencia y el gasto queda con los valores completos de una de las dos (nunca mezclados), respetando el límite. Sin `unittest.mock`.

### Implementation for User Story 2

- [X] T027 [US2] En `app/repositories/gastos.py`: `total_por_categoria(db, usuario_id, categoria, excluir_id=None)` (excluye ese `id` del `SUM` cuando viene) y `bloquear_usuario(db, usuario_id)` con `db.scalars(select(Usuario.id).where(Usuario.id == usuario_id).with_for_update())` (SQLAlchemy, sin SQL crudo). (depende de T022)
- [X] T028 [US2] En `app/services/gastos.py`: helper `_bloquear_usuario(repo, db, usuario_id)` que llama a `getattr(repo, "bloquear_usuario", None)` si existe; invocarlo **antes** de leer el total en `registrar_gasto` y `actualizar_gasto`; en `actualizar_gasto` evaluar el límite con `total_por_categoria(..., excluir_id=gasto_id)` (enviar `excluir_id` solo en la ruta de edición) sobre la categoría **resultante**, lanzando `LimiteExcedidoError` con el mensaje de 001. (depende de T023, T027)

**Checkpoint**: T025 y T026 en verde; el límite no se rompe editando ni en paralelo.

---

## Phase 6: User Story 3 - Buscar, ordenar y resumir (Priority: P2)

**Goal**: listado con filtros, orden y total; resumen por categoría; categorías permitidas.

**Independent Test**: con gastos variados de dos usuarios, listar filtrando/ordenando y consultar resumen y categorías.

### Tests for User Story 3

- [X] T029 [P] [US3] Crear `tests/test_gastos_listado_service.py` (service con repo falso): `listar_gastos` sin filtros llama a `repo.listar(db, usuario_id, skip, limit)` (forma legada); con filtros los reenvía; `contar_gastos` (devuelve `None` si el repo no define `contar`, caso de los dobles de 001); `resumen_gastos` devuelve siempre las 4 categorías (las vacías con total 0, cantidad 0, disponible 500), `disponible` = 500 − total histórico aunque se pase rango, y `total_general`; `info_categorias` coincide con `CATEGORIAS_PERMITIDAS` y límite 500.
- [X] T030 [P] [US3] Crear `tests/test_gastos_integracion_listado.py` (Postgres real): filtros combinados `categoria`, `desde`, `hasta`, `monto_min`, `monto_max` solo devuelven gastos propios; `orden` `fecha`, `-fecha`, `monto`, `-monto`; sin orden, `id` ascendente; empates desempatados por `id`; `contar` coincide con el total filtrado sin paginar; resumen con y sin rango (AC14: 120 en comida y 30 en transporte → `total_general` 150).
- [X] T031 [P] [US3] Crear `tests/test_api_gastos_listado.py` (API): `X-Total-Count` presente y correcto; `desde > hasta`, `monto_min > monto_max` y `orden=otro` → 422; `GET /gastos/resumen` y `GET /gastos/categorias` responden 200 y **no** son capturadas por `/{gasto_id}`; lista vacía → `[]` y `X-Total-Count: 0`; y, con un doble legado sin `contar`, `GET /gastos/?usuario_id=999` → 200 sin header `X-Total-Count` y el repo recibe solo el `usuario_id` del token (regresión del caso de error 5 de 001).

### Implementation for User Story 3

- [X] T032 [US3] En `app/schemas/gasto.py` agregar `FiltrosGastos` (`skip>=0`, `limit` 1-100, `categoria?`, `desde?`, `hasta?`, `monto_min?`, `monto_max?`, `orden?` restringido a `fecha|-fecha|monto|-monto`; validadores cruzados `desde <= hasta` y `monto_min <= monto_max`; **sin** `extra="forbid"`: los query params desconocidos, p. ej. `usuario_id`, se ignoran, como exige el caso de error 5 de 001), `ResumenCategoria` (`categoria`, `total`, `cantidad`, `disponible`), `ResumenGastos` (`categorias`, `total_general`) y `CategoriasResponse` (`categorias`, `limite_por_categoria`). (depende de T014)
- [X] T033 [US3] En `app/repositories/gastos.py`: ampliar `listar(db, usuario_id, skip=0, limit=20, categoria=None, desde=None, hasta=None, monto_min=None, monto_max=None, orden=None)` con `where` por filtro, `order_by` del campo pedido y `Gasto.id` ascendente siempre como desempate/orden por defecto; agregar `contar(db, usuario_id, <mismos filtros>) -> int` y `resumen_por_categoria(db, usuario_id, desde=None, hasta=None) -> list[dict]` con `GROUP BY categoria`. (depende de T027)
- [X] T034 [US3] En `app/services/gastos.py`: ampliar `listar_gastos(db, usuario_id, skip=0, limit=20, <filtros>, repo=…)` enviando los filtros al repo **solo si alguno viene informado**; agregar `contar_gastos` (devuelve `None` si el repo no define `contar`, para tolerar los dobles de 001), `resumen_gastos` (itera `CATEGORIAS_PERMITIDAS`, calcula `disponible` con `total_por_categoria` histórico) e `info_categorias`. (depende de T033)
- [X] T035 [US3] En `app/routers/gastos.py`: `GET /` con `Annotated[FiltrosGastos, Query()]` y `Response` para el header `X-Total-Count` (solo si `contar_gastos` devuelve un valor); insertar `GET /resumen` y `GET /categorias` **por encima** de las rutas `/{gasto_id}` que dejó T024. (depende de T032, T034, T024)

**Checkpoint**: US3 funcional; `/resumen` y `/categorias` no chocan con `/{gasto_id}`.

---

## Phase 7: User Story 5 - Administrar mi cuenta (Priority: P2)

**Goal**: perfil, cambio de email y de contraseña, baja de cuenta con sus gastos; credenciales viejas rechazadas.

**Independent Test**: registrar, consultar `/me`, cambiar email y contraseña, eliminar la cuenta, verificando el acceso en cada paso.

### Tests for User Story 5

- [X] T036 [P] [US5] Crear `tests/test_usuarios_me_service.py` (service con repo falso con `actualizar_email`, `actualizar_password`, `eliminar`): `cambiar_email` con contraseña correcta y email libre; email en uso → `EmailYaRegistradoError`; contraseña incorrecta → `CredencialesInvalidasError`; `cambiar_password` (actual incorrecta → `CredencialesInvalidasError`, nueva igual → `PasswordIgualError`, éxito re-hashea); `eliminar_usuario` con contraseña correcta/incorrecta; emails normalizados a minúsculas en registro y login.
- [X] T037 [P] [US5] Crear `tests/test_api_usuarios_me.py` (API con Postgres vía fixture `client`): `GET /usuarios/me` 200 sin campo de contraseña; `PATCH /usuarios/me` éxito (200 con `access_token` nuevo que funciona), email en uso 400, contraseña incorrecta 400, contraseña no enviada 422; token **anterior** al cambio → 401, también si otro usuario registra después el email viejo (nunca opera como él, AC20); `PUT /usuarios/me/password` 204 / actual incorrecta 400 / igual 400 / <8 o >72 caracteres 422 y login con la nueva; `DELETE /usuarios/me` con contraseña incorrecta 400, sin cuerpo 422 (usar `client.request("DELETE", url, json=…)`, porque `client.delete` de httpx no acepta `json`), correcta 204 y su token → 401; registro con contraseña <8 o >72 → 422 y email con mayúsculas se guarda en minúsculas.
- [X] T038 [P] [US5] Crear `tests/test_usuarios_integracion.py` (Postgres real): `eliminar_usuario` borra sus gastos por `ON DELETE CASCADE` y deja intactos los de otro usuario; `actualizar_email` a un email existente devuelve `None` (captura `IntegrityError`) sin dejar la sesión rota.

### Implementation for User Story 5

- [X] T039 [US5] Actualizar `app/schemas/usuario.py` (todos de entrada con `extra="forbid"`): `UsuarioCreate` con `password` de 8 a 72 caracteres y `email` normalizado a minúsculas; `UsuarioEmailUpdate` (`email`, `password_actual`); `PasswordChange` (`password_actual`, `password_nueva` de 8 a 72); `CuentaDelete` (`password_actual`); `EmailActualizadoResponse` (`id`, `email`, `access_token`, `token_type`). `UsuarioResponse` no incluye contraseña.
- [X] T040 [US5] En `app/repositories/usuarios.py` agregar `actualizar_email(db, usuario, email) -> Usuario | None` (captura `IntegrityError`, hace `rollback` y devuelve `None`) y `eliminar(db, usuario) -> None` (borra la fila; la base elimina los gastos). (depende de T002)
- [X] T041 [US5] En `app/services/usuarios.py`: `PasswordIgualError`; normalizar a minúsculas el email en `registrar_usuario`, `autenticar_usuario` y búsquedas; `cambiar_email(db, usuario, email_nuevo, password_actual, repo=…)`, `cambiar_password(db, usuario, password_actual, password_nueva, repo=…)` y `eliminar_usuario(db, usuario, password_actual, repo=…)`, verificando `password_actual` con `verify_password` (incorrecta → `CredencialesInvalidasError`). (depende de T040)
- [X] T042 [US5] En `app/routers/usuarios.py` agregar `GET /me`, `PATCH /me` (200, emite token nuevo con `{"sub": email, "uid": id}`), `PUT /me/password` (204) y `DELETE /me` (204, cuerpo JSON `CuentaDelete`), con `get_current_user`; mapear `EmailYaRegistradoError`, `CredencialesInvalidasError` y `PasswordIgualError` a 400. (depende de T039, T041, T005)

**Checkpoint**: US5 funcional; el token viejo nunca opera como otro usuario.

---

## Phase 8: User Story 6 - Gestionar desde el asistente MCP (Priority: P3)

**Goal**: tools equivalentes con errores estructurados y confirmación para eliminar.

**Independent Test**: invocar cada tool con datos válidos e inválidos y comprobar que nunca lanza excepción.

### Tests for User Story 6

- [X] T043 [P] [US6] Crear `tests/test_mcp_gastos_crud.py` (llamadas directas a las funciones, patrón de `tests/test_mcp_gastos.py`, Postgres real vía `db_pruebas`; **≥2 tests por tool**, Art. VII.6): `obtener_gasto` (éxito; ajeno/inexistente → `{"error"}`), `actualizar_gasto` (éxito parcial; sin campos/límite excedido/ajeno → `{"error"}`), `eliminar_gasto` (sin `confirmar` → `{"error"}` y el gasto sigue; con `confirmar=True` → elimina; ajeno → `{"error"}`), `resumen_gastos` (4 categorías; fecha inválida → `{"error"}`), `listar_categorias`, y `listar_gastos` con `categoria` y `orden` solo propios; las fechas salen en ISO 8601.

### Implementation for User Story 6

- [X] T044 [US6] En `app/mcp/tools/gastos.py` agregar el helper `_ejecutar(fn)` (abre `SessionLocal`, resuelve usuario con verificación de `uid`, captura `ValueError`, `CategoriaInvalidaError`, `LimiteExcedidoError`, `GastoNoEncontradoError` y `AccesoDenegadoError` → `{"error": str(e)}`, cierra la sesión); migrar `registrar_gasto` (con `fecha?`) y `listar_gastos` (con filtros opcionales) al helper sin cambiar su contrato; serializar `date` con `isoformat()`; corregir el docstring de `registrar_gasto` ("límite acumulado por categoría"). (depende de T028, T034, T006)
- [X] T045 [US6] En `app/mcp/tools/gastos.py` agregar las tools de lectura `obtener_gasto(gasto_id)`, `resumen_gastos(desde?, hasta?)` y `listar_categorias()` sobre `_ejecutar`, llamando solo a `services/gastos.py`, con descripciones específicas y accionables (Art. VI.2). (depende de T044)
- [X] T046 [US6] En `app/mcp/tools/gastos.py` agregar las tools de escritura `actualizar_gasto(gasto_id, descripcion?, monto?, categoria?, fecha?)` (parcial, al menos un campo) y `eliminar_gasto(gasto_id, confirmar=False)` (sin `confirmar=True` devuelve `{"error": "Confirma la eliminación con confirmar=true"}` y no llama al service, Art. VI.5); registrar las 7 tools en `register()`. (depende de T045)

**Checkpoint**: 7 tools registradas; ninguna lanza excepciones al cliente.

---

## Phase 9: User Story 7 - Chequeo de salud (Priority: P3)

**Goal**: `GET /health` sin autenticación: 200 con base sana, 503 si falla.

**Independent Test**: consultar con la base disponible y con una base que falla.

### Tests for User Story 7

- [X] T047 [P] [US7] Crear `tests/test_health.py`: service `estado` con repo falso que devuelve `True`/`False`; repository real contra Postgres devuelve `True`; API: `GET /health` 200 `{"status": "ok", "db": "ok"}` sin token y, con un repo de salud que falla (`dependency_overrides`), 503 `{"status": "degraded", "db": "error"}` (no un 500 genérico).

### Implementation for User Story 7

- [X] T048 [P] [US7] Crear `app/repositories/salud.py` con `base_disponible(db) -> bool` (`db.execute(select(1))` dentro de `try/except SQLAlchemyError`, devuelve `False` si falla).
- [X] T049 [P] [US7] Crear `app/services/salud.py` con `estado(db, repo=salud_repository) -> dict` (`{"status": "ok", "db": "ok"}` o `{"status": "degraded", "db": "error"}`).
- [X] T050 [US7] Crear `app/routers/health.py` (`GET /health` sin auth; 503 cuando `estado` reporta `degraded`; dependencia inyectable para el repo) e incluirlo en `app/main.py` **antes** de `app.mount("/mcp", mcp_app)`. (depende de T048, T049)

**Checkpoint**: US7 funcional.

---

## Phase 10: Polish & Cross-Cutting

- [X] T051 Correr `uv run pytest --cov --cov-report=term-missing` y verificar: todo en verde, 0 warnings (`filterwarnings` ya convierte `DeprecationWarning`/`ResourceWarning` en error), cobertura de `services/` ≥ 90% y del conjunto `services/ + repositories/ + routers/ + utils/` ≥ 80% (Art. VII.3); agregar tests de las ramas sin cubrir si hace falta.
- [X] T052 Verificar el esquema contra la base de desarrollo: `uv run alembic upgrade head` y `uv run alembic check` ("No new upgrade operations detected"); y que ningún símbolo ni ruta del contrato de 001 cambió (revisar `git diff` de firmas en `app/services/gastos.py` y `app/repositories/gastos.py`).
- [X] T053 Ejecutar el recorrido de `specs/002-crud-completo/quickstart.md` (REST, MCP con `tools/list` de las 7 tools, `/health`) y vaciar las tablas de `gastos` al terminar (`TRUNCATE gastos, usuarios RESTART IDENTITY CASCADE`).
- [ ] T054 Dejar al usuario la actualización de `.env.example` (bloqueado para el agente): variables `DATABASE_URL`, `TEST_DATABASE_URL` y `SECRET_KEY` con placeholders; avisar en el reporte final que los tokens emitidos antes del despliegue dejan de valer.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **bloquea todas las historias**. Incluye la enmienda de la constitución (T010), que debe estar aplicada antes de cualquier tarea de gastos que use 204, PUT/PATCH u `obtener_por_id`.
- **US4 (Phase 3)**: depende de Foundational; es prerrequisito de US1 (la respuesta incluye `fecha`).
- **US1 (Phase 4)**: depende de US4.
- **US2 (Phase 5)**: depende de US1 (`actualizar_gasto`, repo `obtener_por_id`).
- **US3 (Phase 6)**: depende de US2 (`total_por_categoria`) y de US1 para el orden de rutas (T035 depende de T024).
- **US5 (Phase 7)**: depende de Foundational (T005); independiente de gastos.
- **US6 (Phase 8)**: depende de US2, US3 y T006.
- **US7 (Phase 9)**: depende solo de Foundational.
- **Polish (Phase 10)**: depende de todas las historias.

### User Story Dependencies

- US4 → US1 → US2 → US3 → US6 (cadena de gastos).
- US5 y US7 son independientes de la cadena de gastos y pueden avanzar en paralelo tras Foundational.

### Within Each User Story

- Tests primero (deben fallar), luego schemas → repository → service → router/tool.
- Una tarea no se da por terminada sin su test en verde (Art. VII.7).
- Archivos compartidos (`app/schemas/gasto.py`, `app/repositories/gastos.py`, `app/services/gastos.py`, `app/routers/gastos.py`) se editan en secuencia, no en paralelo.

### Parallel Opportunities

- Foundational: T004, T006, T008, T009 en paralelo entre sí tras sus dependencias (archivos distintos).
- Cada fase de historia: todas las tareas de tests `[P]` en paralelo (archivos distintos).
- Tras Foundational: **US5 (T036-T042)** y **US7 (T047-T050)** pueden avanzar en paralelo con la cadena de gastos si hay más de una persona o agente.

### Parallel Example: User Story 1

```text
# Tests de US1 en paralelo (archivos distintos):
Task: "tests/test_gastos_crud_service.py"        (T018)
Task: "tests/test_api_gastos_crud.py"            (T019)
Task: "tests/test_gastos_integracion_crud.py"    (T020)
```

### Parallel Example: US5 y US7 junto a la cadena de gastos

```text
Agente A: T011 → T017 (US4) → T018 → T024 (US1) → ...
Agente B: T036 → T042 (US5)
Agente C: T047 → T050 (US7)
```

---

## Implementation Strategy

### MVP First (US4 + US1)

1. Setup + Foundational (T001-T010).
2. US4 (fecha) y US1 (consultar/PUT/PATCH/DELETE).
3. **Detenerse y validar**: el usuario ya puede corregir y eliminar gastos. Es el hueco funcional principal.

### Incremental Delivery

1. + US2 → el límite queda blindado (P1 completo).
2. + US3 → búsqueda y resumen.
3. + US5 → gestión de cuenta (en paralelo posible).
4. + US6 → asistente MCP.
5. + US7 → salud.
6. Polish: enmiendas a la constitución, cobertura, migración y recorrido manual.

### Notas

- Total: 54 tareas (T001-T054).
- Evitar tareas vagas, conflictos en el mismo archivo y dependencias cruzadas entre historias que rompan su independencia.
