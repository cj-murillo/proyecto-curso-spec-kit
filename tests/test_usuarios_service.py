import pytest
from app.services import usuarios as usuarios_service
from app.services.usuarios import EmailYaRegistradoError, CredencialesInvalidasError
from app.security import hash_password


class RepositorioUsuarioFalso:
    """Test double: mismo contrato que app/repositories/usuarios.py, sin persistencia real."""

    class _UsuarioFalso:
        def __init__(self, id_, email, hashed_password):
            self.id = id_
            self.email = email
            self.hashed_password = hashed_password

    def __init__(self):
        self._usuarios: dict[str, "RepositorioUsuarioFalso._UsuarioFalso"] = {}

    def obtener_por_email(self, db, email):
        return self._usuarios.get(email)

    def guardar(self, db, email, hashed_password):
        usuario = self._UsuarioFalso(len(self._usuarios) + 1, email, hashed_password)
        self._usuarios[email] = usuario
        return usuario


def test_registrar_usuario_exitoso():
    repo = RepositorioUsuarioFalso()

    usuario = usuarios_service.registrar_usuario(None, "nuevo@ejemplo.com", "clave123", repo=repo)

    assert usuario.email == "nuevo@ejemplo.com"
    assert usuario.hashed_password != "clave123"


def test_registrar_usuario_duplicado_lanza_error():
    repo = RepositorioUsuarioFalso()
    usuarios_service.registrar_usuario(None, "dup@ejemplo.com", "clave123", repo=repo)

    with pytest.raises(EmailYaRegistradoError):
        usuarios_service.registrar_usuario(None, "dup@ejemplo.com", "otra-clave", repo=repo)


def test_autenticar_usuario_exitoso():
    repo = RepositorioUsuarioFalso()
    repo.guardar(None, "test@ejemplo.com", hash_password("clave123"))

    usuario = usuarios_service.autenticar_usuario(None, "test@ejemplo.com", "clave123", repo=repo)

    assert usuario.email == "test@ejemplo.com"


def test_autenticar_credenciales_invalidas():
    repo = RepositorioUsuarioFalso()
    repo.guardar(None, "test@ejemplo.com", hash_password("clave123"))

    with pytest.raises(CredencialesInvalidasError):
        usuarios_service.autenticar_usuario(None, "test@ejemplo.com", "clave-incorrecta", repo=repo)

    with pytest.raises(CredencialesInvalidasError):
        usuarios_service.autenticar_usuario(None, "no-existe@ejemplo.com", "clave123", repo=repo)
