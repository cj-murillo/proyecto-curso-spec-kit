import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import configurar_logging
from app.routers import usuarios, gastos
from app.mcp.server import mcp as mcp_server

configurar_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Streamable-HTTP: el servidor MCP de este proyecto (mismos tools, mismo
# services/gastos.py), servido como una sub-app ASGI montable en FastAPI.
# Se crea ANTES de entrar al lifespan: mcp_server.session_manager es lazy y
# solo existe después de llamar a streamable_http_app().
mcp_app = mcp_server.streamable_http_app()

# El SDK registra las rutas de metadata OAuth (RFC 9728) DENTRO de mcp_app,
# p. ej. "/.well-known/oauth-protected-resource/mcp". Como mcp_app se monta
# bajo "/mcp", quedarían servidas en "/mcp/.well-known/...", pero el spec
# exige que el cliente las encuentre en la raíz del host. Se separan y se
# agregan directo al app raíz.
rutas_well_known = [
    route for route in mcp_app.routes if getattr(route, "path", "").startswith("/.well-known")
]
mcp_app.routes[:] = [route for route in mcp_app.routes if route not in rutas_well_known]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # mcp_app trae su propio lifespan (arranca el session manager de streamable-http).
    # FastAPI NO lo arranca solo por estar montado con app.mount() -- hay que entrar a él
    # explícitamente, o las conexiones a /mcp fallan o cuelgan.
    try:
        async with mcp_server.session_manager.run():
            yield
    except RuntimeError as e:
        if "can only be called once" not in str(e):
            raise
        # Simplificación consciente para testing: StreamableHTTPSessionManager
        # es de un solo uso por instancia, pero `mcp_server` es un singleton de
        # módulo y cada `TestClient(app)` nuevo re-entra este lifespan. En
        # producción el proceso solo arranca una vez y esta rama nunca se
        # ejecuta; en tests, /mcp ya quedó inoperante para esa sesión, pero el
        # resto de la app (routers REST) sigue funcionando con normalidad.
        yield


app = FastAPI(title="API de Control de Gastos", lifespan=lifespan)
app.include_router(usuarios.router)
app.include_router(gastos.router)
app.router.routes.extend(rutas_well_known)
app.mount("/mcp", mcp_app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duracion_ms,
    )
    return response


@app.exception_handler(Exception)
async def manejar_error_no_controlado(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500, content={"detail": "Error interno del servidor"}
    )
