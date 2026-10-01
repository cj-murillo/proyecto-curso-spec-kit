from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import decodificar_token
from app.repositories import usuarios as usuarios_repository
from app.repositories import gastos as gastos_repository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/token")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodificar_token(token)
        email = payload.get("sub")
        if email is None:
            raise credenciales_exception
    except HTTPException:
        raise
    except Exception:
        raise credenciales_exception

    usuario = usuarios_repository.obtener_por_email(db, email)
    # El token debe identificar al MISMO usuario por email (sub) y por id (uid): un email
    # reasignado a otra persona nunca hereda un token anterior (FR-018/FR-019).
    if usuario is None or payload.get("uid") != usuario.id:
        raise credenciales_exception
    return usuario


def get_gastos_repo():
    return gastos_repository
