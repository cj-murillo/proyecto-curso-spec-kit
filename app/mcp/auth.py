from mcp.server.auth.provider import AccessToken, TokenVerifier
from app.security import decodificar_token


class JWTTokenVerifier(TokenVerifier):
    """Verifica los Bearer tokens de MCP reutilizando el mismo JWT del router REST."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = decodificar_token(token)
        except Exception:
            return None

        email = payload.get("sub")
        if not email:
            return None

        return AccessToken(
            token=token,
            client_id=email,
            scopes=["gastos"],
            expires_at=payload.get("exp"),
            subject=email,
            claims={"uid": payload.get("uid")},
        )
