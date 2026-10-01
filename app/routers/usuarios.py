from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.usuario import (
    CuentaDelete,
    EmailActualizadoResponse,
    PasswordChange,
    UsuarioCreate,
    UsuarioEmailUpdate,
    UsuarioResponse,
)
from app.services import usuarios as usuarios_service
from app.services.usuarios import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    PasswordIgualError,
)
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

    token = crear_access_token({"sub": usuario.email, "uid": usuario.id})
    return {"access_token": token, "token_type": "bearer"}


ERRORES_CUENTA = (EmailYaRegistradoError, CredencialesInvalidasError, PasswordIgualError)


@router.get("/me", response_model=UsuarioResponse)
def perfil(usuario_actual: Usuario = Depends(get_current_user)):
    return usuario_actual


@router.patch("/me", response_model=EmailActualizadoResponse)
def cambiar_email(
    datos: UsuarioEmailUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    try:
        usuario = usuarios_service.cambiar_email(
            db, usuario_actual, datos.email, datos.password_actual
        )
    except ERRORES_CUENTA as e:
        raise HTTPException(status_code=400, detail=str(e))
    # El sub del JWT es el email: se emite una credencial nueva; la anterior deja de valer.
    token = crear_access_token({"sub": usuario.email, "uid": usuario.id})
    return {"id": usuario.id, "email": usuario.email, "access_token": token, "token_type": "bearer"}


@router.put("/me/password", status_code=204)
def cambiar_password(
    datos: PasswordChange,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    try:
        usuarios_service.cambiar_password(
            db, usuario_actual, datos.password_actual, datos.password_nueva
        )
    except ERRORES_CUENTA as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(status_code=204)


@router.delete("/me", status_code=204)
def eliminar_cuenta(
    datos: CuentaDelete,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    try:
        usuarios_service.eliminar_usuario(db, usuario_actual, datos.password_actual)
    except ERRORES_CUENTA as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(status_code=204)
