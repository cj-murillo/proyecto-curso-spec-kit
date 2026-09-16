from mcp.server.fastmcp import FastMCP
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
    if usuario is None:
        # Hay token pero no corresponde a nadie (ej. usuario borrado): se
        # rechaza. NUNCA se cae al usuario demo cuando hay un token de por medio.
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


def registrar_gasto(descripcion: str, monto: float, categoria: str) -> dict:
    """Registra un gasto con descripción, monto y categoría, validando el
    límite mensual acumulado por categoría. Usar cuando el usuario mencione
    una compra o pago que quiere trackear."""
    db = SessionLocal()
    try:
        usuario = _resolver_usuario_actual(db)
        return gastos_service.registrar_gasto(db, usuario.id, descripcion, monto, categoria)
    except (
        ValueError,
        gastos_service.CategoriaInvalidaError,
        gastos_service.LimiteExcedidoError,
    ) as e:
        # Manejo de errores en tools: se devuelve texto claro, no una excepción sin control
        return {"error": str(e)}
    finally:
        db.close()


def listar_gastos(skip: int = 0, limit: int = 20) -> list[dict]:
    """Lista los gastos registrados del usuario autenticado, paginados con
    skip/limit. Usar cuando pregunten por sus gastos o quieran un resumen."""
    db = SessionLocal()
    try:
        usuario = _resolver_usuario_actual(db)
        return gastos_service.listar_gastos(db, usuario.id, skip, limit)
    except ValueError as e:
        # Artículo VI.3: error de negocio como estructura clara, no excepción sin controlar.
        return {"error": str(e)}
    finally:
        db.close()


def register(mcp: FastMCP) -> None:
    """Registra los tools de gastos sobre la instancia de FastMCP que le pasa server.py."""
    mcp.tool()(registrar_gasto)
    mcp.tool()(listar_gastos)
