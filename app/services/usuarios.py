import logging

from app.repositories import usuarios as usuarios_repository
from app.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class EmailYaRegistradoError(Exception):
    pass


class CredencialesInvalidasError(Exception):
    pass


class UsuarioNoEncontradoError(Exception):
    pass


class PasswordIgualError(Exception):
    pass


def registrar_usuario(db, email: str, password: str, repo=usuarios_repository):
    email = email.lower()
    if repo.obtener_por_email(db, email):
        raise EmailYaRegistradoError(f"El email {email} ya está registrado")

    hashed = hash_password(password)
    usuario = repo.guardar(db, email, hashed)
    logger.info("Usuario registrado: usuario_id=%s email=%s", usuario.id, usuario.email)
    return usuario


def autenticar_usuario(db, email: str, password: str, repo=usuarios_repository):
    email = email.lower()
    usuario = repo.obtener_por_email(db, email)
    if not usuario or not verify_password(password, usuario.hashed_password):
        logger.warning("Login fallido: email=%s", email)
        raise CredencialesInvalidasError("Email o contraseña incorrectos")
    return usuario


def resetear_password(db, email: str, nueva_password: str, repo=usuarios_repository):
    email = email.lower()
    usuario = repo.obtener_por_email(db, email)
    if not usuario:
        raise UsuarioNoEncontradoError(f"No existe el usuario {email}")
    repo.actualizar_password(db, usuario, hash_password(nueva_password))
    logger.info("Password reseteada: usuario_id=%s", usuario.id)
    return usuario


def _exigir_password_actual(usuario, password_actual: str) -> None:
    if not verify_password(password_actual, usuario.hashed_password):
        logger.warning("Contraseña actual incorrecta: usuario_id=%s", usuario.id)
        raise CredencialesInvalidasError("La contraseña actual es incorrecta")


def cambiar_email(db, usuario, email_nuevo: str, password_actual: str, repo=usuarios_repository):
    _exigir_password_actual(usuario, password_actual)
    email_nuevo = email_nuevo.lower()
    if email_nuevo == usuario.email:
        return usuario
    existente = repo.obtener_por_email(db, email_nuevo)
    if existente is not None and existente.id != usuario.id:
        raise EmailYaRegistradoError(f"El email {email_nuevo} ya está registrado")
    actualizado = repo.actualizar_email(db, usuario, email_nuevo)
    if actualizado is None:  # carrera: otro lo registró entre la consulta y la escritura
        raise EmailYaRegistradoError(f"El email {email_nuevo} ya está registrado")
    logger.info("Email cambiado: usuario_id=%s", usuario.id)
    return actualizado


def cambiar_password(
    db, usuario, password_actual: str, password_nueva: str, repo=usuarios_repository
):
    _exigir_password_actual(usuario, password_actual)
    if password_nueva == password_actual:
        raise PasswordIgualError("La contraseña nueva debe ser distinta de la actual")
    repo.actualizar_password(db, usuario, hash_password(password_nueva))
    logger.info("Contraseña cambiada: usuario_id=%s", usuario.id)


def eliminar_usuario(db, usuario, password_actual: str, repo=usuarios_repository) -> None:
    _exigir_password_actual(usuario, password_actual)
    repo.eliminar(db, usuario)
    logger.info("Usuario eliminado: usuario_id=%s", usuario.id)
