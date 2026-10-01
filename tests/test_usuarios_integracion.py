import pytest

from app.repositories import gastos as gastos_repository
from app.repositories import usuarios as usuarios_repository
from app.services import usuarios as svc


@pytest.fixture
def db(SessionLocalDePrueba):
    sesion = SessionLocalDePrueba()
    yield sesion
    sesion.close()


def test_eliminar_usuario_borra_sus_gastos_y_no_los_de_otro(db):
    ana = svc.registrar_usuario(db, "ana@ejemplo.com", "clave12345")
    beto = svc.registrar_usuario(db, "beto@ejemplo.com", "clave12345")
    ana_id, beto_id = ana.id, beto.id
    gastos_repository.guardar(db, ana_id, "de ana", 10.0, "comida")
    gastos_repository.guardar(db, beto_id, "de beto", 20.0, "comida")

    svc.eliminar_usuario(db, ana, "clave12345")

    assert usuarios_repository.obtener_por_email(db, "ana@ejemplo.com") is None
    assert gastos_repository.contar(db, ana_id) == 0
    assert gastos_repository.contar(db, beto_id) == 1


def test_actualizar_email_a_uno_existente_devuelve_none_y_la_sesion_sigue_usable(db):
    ana = svc.registrar_usuario(db, "ana@ejemplo.com", "clave12345")
    svc.registrar_usuario(db, "beto@ejemplo.com", "clave12345")

    assert usuarios_repository.actualizar_email(db, ana, "beto@ejemplo.com") is None
    db.refresh(ana)
    assert ana.email == "ana@ejemplo.com"
    assert usuarios_repository.obtener_por_email(db, "beto@ejemplo.com") is not None
