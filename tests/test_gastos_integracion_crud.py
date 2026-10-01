import pytest

from app.repositories import gastos as gastos_repository
from app.repositories import usuarios as usuarios_repository
from app.services import gastos as svc
from app.services.gastos import AccesoDenegadoError


@pytest.fixture
def db(SessionLocalDePrueba):
    sesion = SessionLocalDePrueba()
    yield sesion
    sesion.close()


@pytest.fixture
def dos_usuarios(db):
    a = usuarios_repository.guardar(db, "a@ejemplo.com", "h")
    b = usuarios_repository.guardar(db, "b@ejemplo.com", "h")
    return a, b


def test_ciclo_completo_con_repositorio_real(db, dos_usuarios):
    a, _ = dos_usuarios
    g = svc.registrar_gasto(db, a.id, "Almuerzo", 10.0, "comida", repo=gastos_repository)

    assert svc.obtener_gasto(db, a.id, g["id"], repo=gastos_repository)["monto"] == 10.0
    reemplazado = svc.actualizar_gasto(
        db, a.id, g["id"],
        {"descripcion": "Cena", "monto": 20.0, "categoria": "otros", "fecha": g["fecha"]},
        repo=gastos_repository,
    )
    assert reemplazado["descripcion"] == "Cena"
    parcial = svc.actualizar_gasto(db, a.id, g["id"], {"monto": 25.5}, repo=gastos_repository)
    assert parcial["monto"] == 25.5 and parcial["descripcion"] == "Cena"
    svc.eliminar_gasto(db, a.id, g["id"], repo=gastos_repository)
    assert gastos_repository.obtener_por_id(db, g["id"]) is None


def test_otro_usuario_no_puede_leer_modificar_ni_borrar(db, dos_usuarios):
    a, b = dos_usuarios
    g = svc.registrar_gasto(db, a.id, "Privado", 10.0, "comida", repo=gastos_repository)

    for operacion in (
        lambda: svc.obtener_gasto(db, b.id, g["id"], repo=gastos_repository),
        lambda: svc.actualizar_gasto(db, b.id, g["id"], {"monto": 1.0}, repo=gastos_repository),
        lambda: svc.eliminar_gasto(db, b.id, g["id"], repo=gastos_repository),
    ):
        with pytest.raises(AccesoDenegadoError):
            operacion()

    intacto = gastos_repository.obtener_por_id(db, g["id"])
    assert intacto["monto"] == 10.0 and intacto["descripcion"] == "Privado"


def test_repositorio_actualizar_y_eliminar_filtran_por_usuario(db, dos_usuarios):
    a, b = dos_usuarios
    g = gastos_repository.guardar(db, a.id, "x", 5.0, "otros")

    assert gastos_repository.actualizar(db, g["id"], b.id, "y", 1.0, "otros", g["fecha"]) is None
    assert gastos_repository.eliminar(db, g["id"], b.id) is False
    assert gastos_repository.obtener_por_id(db, g["id"])["descripcion"] == "x"
