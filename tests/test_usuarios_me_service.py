import pytest

from app.security import hash_password, verify_password
from app.services import usuarios as svc
from app.services.usuarios import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    PasswordIgualError,
)


class _Usuario:
    def __init__(self, id_, email, password):
        self.id = id_
        self.email = email
        self.hashed_password = hash_password(password)


class RepoUsuarios:
    def __init__(self, *usuarios):
        self.usuarios = {u.email: u for u in usuarios}
        self.eliminados = []
        self.carrera = False  # simula que otro registra el email justo antes de escribir

    def obtener_por_email(self, db, email):
        return self.usuarios.get(email)

    def guardar(self, db, email, hashed_password):
        u = _Usuario(len(self.usuarios) + 1, email, "x")
        u.hashed_password = hashed_password
        self.usuarios[email] = u
        return u

    def actualizar_email(self, db, usuario, email):
        if self.carrera:
            return None
        del self.usuarios[usuario.email]
        usuario.email = email
        self.usuarios[email] = usuario
        return usuario

    def actualizar_password(self, db, usuario, hashed_password):
        usuario.hashed_password = hashed_password

    def eliminar(self, db, usuario):
        self.eliminados.append(usuario.id)
        del self.usuarios[usuario.email]


@pytest.fixture
def ana():
    return _Usuario(1, "ana@ejemplo.com", "clave12345")


def test_cambiar_email_con_password_correcta_y_email_libre(ana):
    repo = RepoUsuarios(ana)
    u = svc.cambiar_email(None, ana, "NUEVO@Ejemplo.com", "clave12345", repo=repo)
    assert u.email == "nuevo@ejemplo.com"


def test_cambiar_email_en_uso_lanza_email_ya_registrado(ana):
    otro = _Usuario(2, "otro@ejemplo.com", "x")
    with pytest.raises(EmailYaRegistradoError):
        svc.cambiar_email(None, ana, "otro@ejemplo.com", "clave12345", repo=RepoUsuarios(ana, otro))


def test_cambiar_email_ante_carrera_lanza_email_ya_registrado(ana):
    repo = RepoUsuarios(ana)
    repo.carrera = True
    with pytest.raises(EmailYaRegistradoError):
        svc.cambiar_email(None, ana, "libre@ejemplo.com", "clave12345", repo=repo)


def test_cambiar_email_con_password_incorrecta_no_cambia_nada(ana):
    with pytest.raises(CredencialesInvalidasError):
        svc.cambiar_email(None, ana, "nuevo@ejemplo.com", "mala", repo=RepoUsuarios(ana))
    assert ana.email == "ana@ejemplo.com"


def test_cambiar_email_al_mismo_email_no_falla(ana):
    assert svc.cambiar_email(None, ana, "ANA@ejemplo.com", "clave12345", repo=RepoUsuarios(ana)) is ana


def test_cambiar_password_exitoso_re_hashea(ana):
    svc.cambiar_password(None, ana, "clave12345", "otra-clave-99", repo=RepoUsuarios(ana))
    assert verify_password("otra-clave-99", ana.hashed_password)
    assert not verify_password("clave12345", ana.hashed_password)


def test_cambiar_password_actual_incorrecta_o_nueva_igual(ana):
    repo = RepoUsuarios(ana)
    with pytest.raises(CredencialesInvalidasError):
        svc.cambiar_password(None, ana, "mala", "otra-clave-99", repo=repo)
    with pytest.raises(PasswordIgualError):
        svc.cambiar_password(None, ana, "clave12345", "clave12345", repo=repo)
    assert verify_password("clave12345", ana.hashed_password)


def test_eliminar_usuario_con_password_correcta_e_incorrecta(ana):
    repo = RepoUsuarios(ana)
    with pytest.raises(CredencialesInvalidasError):
        svc.eliminar_usuario(None, ana, "mala", repo=repo)
    assert repo.eliminados == []
    svc.eliminar_usuario(None, ana, "clave12345", repo=repo)
    assert repo.eliminados == [1]


def test_registro_y_login_normalizan_el_email_a_minusculas():
    repo = RepoUsuarios()
    u = svc.registrar_usuario(None, "Mixto@Ejemplo.COM", "clave12345", repo=repo)
    assert u.email == "mixto@ejemplo.com"
    assert svc.autenticar_usuario(None, "MIXTO@ejemplo.com", "clave12345", repo=repo) is u
    with pytest.raises(EmailYaRegistradoError):
        svc.registrar_usuario(None, "mixto@EJEMPLO.com", "clave12345", repo=repo)
