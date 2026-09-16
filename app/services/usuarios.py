import logging

from app.repositories import usuarios as usuarios_repository
from app.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class EmailYaRegistradoError(Exception):
    pass


class CredencialesInvalidasError(Exception):
    pass


def registrar_usuario(db, email: str, password: str, repo=usuarios_repository):
    if repo.obtener_por_email(db, email):
        raise EmailYaRegistradoError(f"El email {email} ya está registrado")

    hashed = hash_password(password)
    usuario = repo.guardar(db, email, hashed)
    logger.info("Usuario registrado: usuario_id=%s email=%s", usuario.id, usuario.email)
    return usuario


def autenticar_usuario(db, email: str, password: str, repo=usuarios_repository):
    usuario = repo.obtener_por_email(db, email)
    if not usuario or not verify_password(password, usuario.hashed_password):
        logger.warning("Login fallido: email=%s", email)
        raise CredencialesInvalidasError("Email o contraseña incorrectos")
    return usuario
