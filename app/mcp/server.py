from mcp.server.mcpserver import MCPServer
from app.mcp.tools import gastos
from mcp.server.auth.settings import AuthSettings
from app.config import settings
from app.mcp.auth import JWTTokenVerifier

mcp = MCPServer(
    "gastos-server",
    token_verifier=JWTTokenVerifier(),
    auth=AuthSettings(
        issuer_url=settings.mcp_issuer_url,
        resource_server_url=settings.mcp_resource_url,
        required_scopes=["gastos"],
        # Simplificación consciente: el JWT de este proyecto no trae el claim de
        # audiencia (resource), así que no pedimos al SDK que lo valide. En un
        # sistema real, el token debe emitirse para ESTE servidor y esto va en True.
        validate_token_resource=False,
    ),
)
gastos.register(mcp)

if __name__ == "__main__":
    mcp.run()
