# Feature Specification: Control de Gastos

**Feature Branch**: `001-control-de-gastos`

**Created**: 2026-09-14

**Status**: Draft

**Input**: Sistema de control de gastos personales — reconstrucción del proyecto de las
Sesiones 6-8 (arquitectura en capas, OAuth2+JWT, SQLAlchemy+Alembic, MCP reutilizando
`services/`) siguiendo Spec-Driven Development.

## Entidades

- **Usuario**: email (único), contraseña (nunca expuesta en respuestas).
- **Gasto**: descripción, monto (> 0), categoría, pertenece a un usuario (`usuario_id`).

## Reglas de negocio

1. Categorías válidas: `comida`, `transporte`, `entretenimiento`, `otros`. Cualquier otra
   categoría es un error de negocio (`CategoriaInvalidaError`), no una excepción genérica.
2. El monto de un gasto debe ser mayor a cero; una descripción vacía también es inválida.
   Ambos casos son `ValueError`.
3. Un gasto no puede hacer que el total acumulado de su categoría supere 500 (constante
   `LIMITE_POR_CATEGORIA`). Si lo supera, es `LimiteExcedidoError`.
4. Un usuario solo puede ver y crear gastos propios; nunca los de otro usuario, sin
   importar qué identificador se pase en la solicitud — el `usuario_id` se ignora si viene
   del cliente y se reemplaza siempre por el del token JWT decodificado.
5. No existe rol de administrador en este alcance. Ningún usuario puede ver, crear ni
   modificar gastos de otro usuario, sin excepción por rol.

## Contrato de la API (REST)

| Método | Ruta              | Auth | Request                          | Éxito         | Errores esperados                                     |
|--------|-------------------|------|-----------------------------------|---------------|--------------------------------------------------------|
| POST   | /usuarios/        | No   | email, password                   | 201 Usuario   | 400 email duplicado, 422 validación                    |
| POST   | /usuarios/token   | No   | username, password (form)         | 200 token JWT | 401 credenciales inválidas                             |
| POST   | /gastos/          | Sí   | descripcion, monto, categoria     | 201 Gasto     | 400 categoría inválida, 400 límite excedido, 401, 422  |
| GET    | /gastos/          | Sí   | query: skip, limit                | 200 lista     | 401, 422 (skip/limit inválidos)                        |

## Contrato equivalente por MCP

- Tool `registrar_gasto(descripcion, monto, categoria)`: mismo comportamiento y mismas
  reglas que `POST /gastos/`, devolviendo el gasto creado o un error de negocio
  estructurado (`{"error": "..."}`).
- Tool `listar_gastos(skip=0, limit=20)`: mismo comportamiento que `GET /gastos/`.
- Ambas tools operan siempre sobre el usuario autenticado de la sesión MCP (identidad
  resuelta desde el token verificado cuando el transporte es `streamable-http`; usuario
  demo de `.env` solo como fallback documentado cuando el transporte es `stdio` sin
  identidad propagable), nunca sobre un usuario indicado como parámetro.

## Contrato de compatibilidad (no negociable)

Los tests de las Sesiones 6-8 se copian a este proyecto **sin modificar sus aserciones**.
Fijan estas firmas — cualquier tarea de `tasks.md` que las cambie viola el Artículo VIII
de la constitución:

### `app/services/gastos.py`
- `CategoriaInvalidaError(Exception)`, `LimiteExcedidoError(Exception)` definidas aquí.
- `LIMITE_POR_CATEGORIA = 500.0`
- `registrar_gasto(db, usuario_id, descripcion, monto, categoria, repo=gastos_repository) -> dict`
  - `monto <= 0` o descripción vacía → `ValueError`
  - categoría no permitida → `CategoriaInvalidaError`
  - `total_actual + monto > 500` → `LimiteExcedidoError`
  - orden posicional exacto; `repo` es keyword con default (DIP, Artículo II.3).
- `listar_gastos(db, usuario_id, skip=0, limit=20, repo=gastos_repository) -> list[dict]`

### `app/repositories/gastos.py` — módulo con funciones, NO clase
- `guardar(db, usuario_id, descripcion, monto, categoria) -> dict`
- `listar(db, usuario_id, skip=0, limit=20) -> list[dict]`
- `total_por_categoria(db, usuario_id, categoria) -> float` (`0.0` si no hay filas)
- Devuelven `dict` con claves `id, descripcion, monto, categoria` — NUNCA objetos ORM.

### `app/repositories/usuarios.py`
- `obtener_por_email(db, email) -> Usuario | None`
- `guardar(db, email, hashed_password) -> Usuario` (devuelve el objeto, con `.id`)

### Otros símbolos importados directamente por los tests copiados
- `app.database`: `Base`, `get_db`, `SessionLocal`, `engine`
- `app.dependencies`: `get_current_user`, `get_gastos_repo`
- `app.models.usuario.Usuario(id=, email=, hashed_password=)`
- `app.main.app`, con `@app.exception_handler(Exception)` que devuelve `500` +
  `{"detail": "Error interno del servidor"}` sin filtrar el stack trace.
- `POST /gastos/` obtiene el repositorio vía `Depends(get_gastos_repo)`, para que
  `app.dependency_overrides[get_gastos_repo]` funcione en los tests de API.
- `tests/__init__.py` debe existir: `test_api_gastos.py` hace
  `from tests.test_gastos import RepositorioFalso`.

## Casos de error explícitos que deben tener test

1. Registrar gasto con monto negativo o cero.
2. Registrar gasto con categoría inexistente.
3. Registrar gasto que excede el límite de 500 en su categoría.
4. Listar o registrar gastos sin token → 401.
5. Listar gastos de otro usuario pasando su ID manualmente → debe ignorarse, nunca debe
   filtrar por ese ID.

## Assumptions

- No hay rol de administrador en este alcance (ver regla de negocio 5) — resuelto por
  `/speckit-clarify`, ver sección siguiente.
- El límite de 500 por categoría es total acumulado histórico, no mensual (el proyecto de
  referencia no resetea por mes; replicar ese comportamiento).
- `skip`/`limit` inválidos (negativos o no numéricos) son error de validación de schema
  (`422`), consistente con el Artículo V.2 de la constitución.

## Clarifications

### Session 2026-09-14

- Q: ¿Puede un usuario con algún rol especial (ej. administrador) ver o modificar gastos
  que no son suyos? → A: No. No existe rol de administrador en este alcance; todo acceso a
  gastos está limitado al usuario dueño, sin excepción. Reflejado en la regla de negocio 5.
