# Research: CRUD completo de gastos y usuario

No quedaron `NEEDS CLARIFICATION` en el Technical Context. Esta fase fija las decisiones técnicas con sus alternativas.

## D1. Límite de 500 seguro bajo concurrencia (FR-007, SC-002)

- **Decisión**: bloqueo de fila del usuario con `select(Usuario.id).where(Usuario.id == uid).with_for_update()` en `repositories/gastos.py::bloquear_usuario` (consulta sobre el modelo `Usuario`, que el repository puede importar). El service lo invoca al inicio de `registrar_gasto` y `actualizar_gasto`; el bloqueo dura hasta el `commit` del propio `guardar/actualizar` (o hasta el cierre de la sesión si se lanza un error), por lo que comprobación y escritura son atómicas por usuario.
- **Justificación**: el límite es por usuario y categoría; serializar por usuario es simple, no requiere SQL crudo (Art. III.1) y no bloquea a otros usuarios. Bajo `READ COMMITTED` (por defecto en Postgres) la segunda petición, tras esperar el bloqueo, ve el commit de la primera al calcular el total.
- **Alternativas**: `pg_advisory_xact_lock` (requiere SQL específico del motor); restricción `CHECK`/trigger en la base (no puede expresar una suma entre filas sin trigger); nivel `SERIALIZABLE` con reintentos (más complejo y exige reintentar en el router); no proteger (descartada por decisión de clarificación).
- **Verificación**: `tests/test_concurrencia_limite.py` lanza dos hilos con sesiones propias sobre `gastos_test` (400 + 60 + 60 → un 201, un 400, total 460).

## D2. Dueño y códigos 403/404 (FR-001, Art. IV.4/V.1)

- **Decisión**: `obtener_por_id(db, gasto_id)` devuelve el dict (incluye `usuario_id`) o `None`. `_cargar_gasto_propio` lanza `GastoNoEncontradoError` (404) o `AccesoDenegadoError` (403). `actualizar` y `eliminar` del repository filtran por `id` **y** `usuario_id` (defensa en profundidad).
- **Alternativa descartada**: devolver 404 también para ajenos (no revela existencia). La constitución reserva 403 para este caso y el usuario lo pidió; se acepta que permite enumerar ids existentes (el contenido nunca se expone).

## D3. PUT y PATCH comparten una operación (FR-002/003)

- **Decisión**: `actualizar_gasto(db, usuario_id, gasto_id, cambios: dict, repo=…)`. PUT envía los 4 campos (el schema los exige); PATCH envía solo los presentes (`model_dump(exclude_unset=True)`). El service mezcla con el gasto actual, valida el resultado completo y evalúa el límite con `total_por_categoria(…, excluir_id=gasto_id)` sobre la categoría resultante.
- **Alternativa**: dos funciones separadas (duplica validación y regla del límite).

## D4. Credencial con `uid` (FR-018, FR-019)

- **Decisión**: `crear_access_token({"sub": email, "uid": id})`. `get_current_user` resuelve por `sub` y exige `payload["uid"] == usuario.id`; el verificador MCP expone `uid` en `AccessToken.claims` y `_resolver_usuario_actual` aplica la misma comparación. Sin `uid` → 401.
- **Alternativa**: cambiar `sub` a `id` (rompe Art. IV.2 y el contrato de tres sitios); lista de revocación (estado extra innecesario).

## D5. Contraseña actual en cambio de email y baja (clarificación 1)

- **Decisión**: `PATCH /usuarios/me` recibe `{"email", "password_actual"}`; `DELETE /usuarios/me` recibe `{"password_actual"}` en el cuerpo. Contraseña incorrecta → 400; contraseña no enviada (o cuerpo vacío en `DELETE`) → 422 por schema.
- **Riesgo**: algunos proxies descartan el cuerpo de `DELETE`. Mitigación: se documenta en el contrato; el cliente de pruebas lo envía con `client.request("DELETE", …, json=…)`.
- **Alternativa**: `POST /usuarios/me/eliminar` (no RESTful; descartada).

## D6. Validación de `monto` con dos decimales (FR-012)

- **Decisión**: tipo anotado `Monto` = `float` con `gt=0`, `le=1_000_000` y validador que comprueba `Decimal(str(valor)).as_tuple().exponent >= -2`. La columna sigue siendo `Float` (cambiar a `Numeric` rompe el contrato de dicts de Art. VIII).
- **Alternativa**: `Decimal` extremo a extremo (cambia tipos de respuesta y de los dobles de prueba).

## D7. Categorías como fuente única (FR-011, Art. II.2)

- **Decisión**: `Categoria = Enum("Categoria", {c: c for c in sorted(CATEGORIAS_PERMITIDAS)})` generado en `schemas/gasto.py`; `info_categorias` y la validación del service leen el mismo conjunto. El resumen itera ese conjunto para incluir categorías sin gastos (clarificación 3).

## D8. Listado: filtros, orden, total (FR-008/009, clarificación 2)

- **Decisión**: modelo `FiltrosGastos` con validadores cruzados (`desde <= hasta`, `monto_min <= monto_max`) y `orden` restringido a `fecha|-fecha|monto|-monto`, recibido con `Annotated[FiltrosGastos, Query()]`. El repository aplica los filtros con `where`, ordena por el campo pedido y **siempre** añade `Gasto.id` ascendente como desempate/orden por defecto. El total sin paginar sale de `contar(...)` con los mismos filtros y el router lo pone en `X-Total-Count`. Si el repo no define `contar` (dobles de 001), `contar_gastos` devuelve `None` y el router omite el header. Los query params desconocidos se ignoran (el modelo no usa `extra="forbid"`), conservando el caso de error 5 de 001.

## D9. Migración (FR-005/006/017, Art. III)

- **Decisión**: una revisión con `down_revision = "7c1d2e9a4b30"`: añadir `fecha` con `server_default=current_date()` (Postgres rellena filas existentes en el mismo `ALTER`), localizar la FK a `usuarios` con `sa.inspect(bind).get_foreign_keys` (el nombre no está fijado), recrearla como `fk_gastos_usuario_id` con `ondelete="CASCADE"`, crear `ix_gastos_usuario_id` y normalizar `usuarios.email` a minúsculas con SQLAlchemy Core. `downgrade` revierte fecha, índice y FK; la normalización de emails no se revierte (documentado).
- **Riesgo**: dos emails que solo difieran en mayúsculas rompen el índice único; la migración aborta sin cambios (DDL transaccional). Con la base actual (sin datos reales) no ocurre.

## D10. Baja de cuenta (FR-017)

- **Decisión**: `eliminar_usuario` borra la fila de `usuarios`; la FK `ON DELETE CASCADE` elimina sus gastos en la base. No se añade relación ORM (evita importación circular y `passive_deletes`).

## D11. Salud (FR-022)

- **Decisión**: `routers/health.py` → `services/salud.py::estado` → `repositories/salud.py::base_disponible` (`select(1)` con `try/except SQLAlchemyError`). Responde 200 `{"status":"ok","db":"ok"}` o 503 `{"status":"degraded","db":"error"}`. Sin autenticación. Se deja pasar por el middleware de logging (impacto bajo; cada sondeo queda en el log).

## D12. Tools MCP (FR-020/021)

- **Decisión**: helper `_ejecutar(fn)` en `mcp/tools/gastos.py` (abre sesión, resuelve usuario con verificación de `uid`, captura errores de dominio → `{"error": …}`, cierra la sesión). Las dos tools existentes se reescriben sobre el helper sin cambiar su contrato. Las fechas se devuelven en ISO 8601 (`date.isoformat()`). `eliminar_gasto(gasto_id, confirmar=False)` no llama al service sin `confirmar=True`.
- **Nota de prueba**: por el workaround del lifespan en `main.py`, los tests llaman las funciones directamente (patrón de `tests/test_mcp_gastos.py`), no por HTTP en `/mcp`.

## D13. Zona horaria

- **Decisión**: "hoy" es `date.today()` del servidor. Sin zonas horarias por usuario (supuesto de la spec).

## D14. Compatibilidad de validación con 001 (decidido al implementar)

- **Decisión**: el schema (422) valida solo lo **nuevo** de 002: descripción recortada y ≤200 caracteres, monto ≤1.000.000 y ≤2 decimales, fecha no futura, `extra="forbid"` en PUT/PATCH y cuerpos de `/usuarios/me*`. Las reglas que en 001 ya eran de negocio (descripción vacía, monto ≤0, categoría inválida) siguen en el service y responden 400, y `POST /gastos/` ignora campos desconocidos: son aserciones de 001 que no se pueden cambiar (Art. VIII; `test_crear_gasto_ignora_usuario_id_del_body`, contrato REST 001).
- **Efecto sobre D7**: no se usa un `Enum` de categorías en los schemas (daría 422 en vez de 400); `CATEGORIAS_PERMITIDAS` sigue siendo la fuente única, consumida por `categoria_valida` e `info_categorias`.
- **Firma**: los parámetros nuevos de los services (`fecha`, filtros) van **después** de `repo=` para conservar nombre y orden de los existentes (Art. VIII).
