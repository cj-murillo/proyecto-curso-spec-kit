from datetime import date

from mcp.server.mcpserver import MCPServer
from app.config import settings
from app.database import SessionLocal
from app.repositories import usuarios as usuarios_repository
from app.services import gastos as gastos_service
from app.security import hash_password
from mcp.server.auth.middleware.auth_context import get_access_token


def _resolver_usuario_actual(db):
    """
    Resuelve el usuario de la sesión MCP actual.

    Artículo VI.4: si hay un token verificado (transporte streamable-http), la
    identidad SIEMPRE sale de ese token — nunca se cae al usuario demo cuando
    hay un token de por medio. El usuario demo es solo el fallback legítimo
    para stdio sin identidad propagable (Artículo VI.4, simplificación
    consciente documentada, no un olvido).
    """
    access_token = get_access_token()
    if access_token is None:
        # stdio sin autenticación: no hay forma de propagar identidad real.
        return _obtener_o_crear_usuario_demo(db)

    usuario = None
    if access_token.subject:
        usuario = usuarios_repository.obtener_por_email(db, access_token.subject)
    claims = getattr(access_token, "claims", None) or {}
    if usuario is None or claims.get("uid") != usuario.id:
        # Hay token pero no corresponde a nadie (ej. usuario borrado o email
        # reasignado): se rechaza. NUNCA se cae al usuario demo cuando hay un token.
        raise ValueError("El token no corresponde a ningún usuario registrado")
    return usuario


def _obtener_o_crear_usuario_demo(db):
    """
    Simplificación intencional documentada (Artículo VI.4): solo se usa cuando
    el transporte es stdio y no hay JWT que propagar. El email/password del
    usuario demo vienen de Settings (.env), no quemados en el código -- mismo
    patrón que SECRET_KEY/DATABASE_URL (Artículo IV.3).
    """
    usuario = usuarios_repository.obtener_por_email(db, settings.mcp_demo_email)
    if usuario is None:
        usuario = usuarios_repository.guardar(
            db, settings.mcp_demo_email, hash_password(settings.mcp_demo_password)
        )
    return usuario


ERRORES_DE_NEGOCIO = (
    ValueError,
    gastos_service.CategoriaInvalidaError,
    gastos_service.LimiteExcedidoError,
    gastos_service.GastoNoEncontradoError,
    gastos_service.AccesoDenegadoError,
)


def _ejecutar(fn):
    """Abre sesión, resuelve al usuario con la identidad del token y ejecuta `fn(db, usuario)`.

    Artículo VI.3: cualquier error de negocio, de inexistencia o de dueño se devuelve como
    {"error": "..."}; nunca una excepción sin controlar que rompa la sesión del cliente MCP."""
    db = SessionLocal()
    try:
        usuario = _resolver_usuario_actual(db)
        return fn(db, usuario)
    except ERRORES_DE_NEGOCIO as e:
        return {"error": str(e)}
    finally:
        db.close()


def _fecha(valor: str | None, campo: str = "fecha") -> date | None:
    if valor is None:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValueError(f"'{campo}' debe tener formato YYYY-MM-DD") from None


def _serializar(gasto: dict) -> dict:
    """Las fechas se devuelven en ISO 8601 (el cliente MCP recibe JSON)."""
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in gasto.items()}


def registrar_gasto(
    descripcion: str, monto: float, categoria: str, fecha: str | None = None
) -> dict:
    """Registra un gasto con descripción, monto y categoría (y fecha YYYY-MM-DD opcional,
    por defecto hoy), validando el límite acumulado por categoría. Usar cuando el usuario
    mencione una compra o pago que quiere trackear."""

    def operacion(db, usuario):
        extra = {} if fecha is None else {"fecha": _fecha(fecha)}
        return _serializar(
            gastos_service.registrar_gasto(db, usuario.id, descripcion, monto, categoria, **extra)
        )

    return _ejecutar(operacion)


def listar_gastos(
    skip: int = 0,
    limit: int = 20,
    categoria: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
    orden: str | None = None,
) -> list[dict]:
    """Lista los gastos del usuario autenticado, paginados con skip/limit, con filtros
    opcionales por categoría, rango de fechas (desde/hasta, YYYY-MM-DD) y de montos, y orden
    (fecha, -fecha, monto, -monto). Usar cuando pregunten por sus gastos."""

    def operacion(db, usuario):
        gastos = gastos_service.listar_gastos(
            db, usuario.id, skip, limit,
            categoria=categoria, desde=_fecha(desde, "desde"), hasta=_fecha(hasta, "hasta"),
            monto_min=monto_min, monto_max=monto_max, orden=orden,
        )
        return [_serializar(g) for g in gastos]

    return _ejecutar(operacion)


def obtener_gasto(gasto_id: int) -> dict:
    """Obtiene un gasto propio por su id (descripción, monto, categoría y fecha). Usar cuando
    el usuario pregunte por un gasto concreto."""
    return _ejecutar(
        lambda db, usuario: _serializar(gastos_service.obtener_gasto(db, usuario.id, gasto_id))
    )


def resumen_gastos(desde: str | None = None, hasta: str | None = None) -> dict:
    """Resume los gastos del usuario por categoría (total, cantidad y cuánto falta para el
    límite de 500) más el total general; desde/hasta (YYYY-MM-DD) acotan total y cantidad.
    Usar cuando pregunten cuánto han gastado."""
    return _ejecutar(
        lambda db, usuario: gastos_service.resumen_gastos(
            db, usuario.id, _fecha(desde, "desde"), _fecha(hasta, "hasta")
        )
    )


def listar_categorias() -> dict:
    """Lista las categorías de gasto permitidas y el límite acumulado por categoría. Usar
    antes de registrar un gasto si no se sabe qué categoría corresponde."""
    return _ejecutar(lambda db, usuario: gastos_service.info_categorias())


def actualizar_gasto(
    gasto_id: int,
    descripcion: str | None = None,
    monto: float | None = None,
    categoria: str | None = None,
    fecha: str | None = None,
) -> dict:
    """Modifica parcialmente un gasto propio: envía solo los campos a cambiar (descripción,
    monto, categoría, fecha YYYY-MM-DD); revalida el límite acumulado por categoría. Usar cuando
    el usuario quiera corregir un gasto."""

    def operacion(db, usuario):
        cambios = {
            k: v
            for k, v in {
                "descripcion": descripcion,
                "monto": monto,
                "categoria": categoria,
                "fecha": _fecha(fecha),
            }.items()
            if v is not None
        }
        return _serializar(gastos_service.actualizar_gasto(db, usuario.id, gasto_id, cambios))

    return _ejecutar(operacion)


def eliminar_gasto(gasto_id: int, confirmar: bool = False) -> dict:
    """Elimina un gasto propio de forma permanente. DESTRUCTIVO: sin confirmar=true no borra
    nada y pide confirmación (Artículo VI.5). Usar solo cuando el usuario lo pida expresamente."""
    if not confirmar:
        return {"error": "Confirma la eliminación con confirmar=true"}

    def operacion(db, usuario):
        gastos_service.eliminar_gasto(db, usuario.id, gasto_id)
        return {"eliminado": True, "id": gasto_id}

    return _ejecutar(operacion)


def register(mcp: MCPServer) -> None:
    """Registra los tools de gastos sobre la instancia de MCPServer que le pasa server.py."""
    for tool in (
        registrar_gasto,
        listar_gastos,
        obtener_gasto,
        actualizar_gasto,
        eliminar_gasto,
        resumen_gastos,
        listar_categorias,
    ):
        mcp.tool()(tool)
