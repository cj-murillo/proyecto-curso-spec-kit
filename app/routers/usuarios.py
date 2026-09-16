from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioResponse
from app.services import usuarios as usuarios_service
from app.services.usuarios import EmailYaRegistradoError, CredencialesInvalidasError
from app.security import crear_access_token

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("/", response_model=UsuarioResponse, status_code=201)
def registrar(datos: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        return usuarios_service.registrar_usuario(db, datos.email, datos.password)
    except EmailYaRegistradoError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        usuario = usuarios_service.autenticar_usuario(db, form.username, form.password)
    except CredencialesInvalidasError as e:
        raise HTTPException(status_code=401, detail=str(e))

    token = crear_access_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}
