from datetime import date, timedelta

import pytest

from app.services import gastos as svc
from app.services.gastos import AccesoDenegadoError, CategoriaInvalidaError, GastoNoEncontradoError
from tests.fakes import RepoGastosEnMemoria


@pytest.fixture
def repo():
    return RepoGastosEnMemoria()


def test_obtener_gasto_propio_no_expone_usuario_id(repo):
    g = repo.sembrar(1, "Almuerzo", 12.5)
    gasto = svc.obtener_gasto(None, 1, g["id"], repo=repo)
    assert gasto["descripcion"] == "Almuerzo"
    assert "usuario_id" not in gasto


def test_obtener_inexistente_lanza_no_encontrado(repo):
    with pytest.raises(GastoNoEncontradoError):
        svc.obtener_gasto(None, 1, 99, repo=repo)


def test_obtener_ajeno_lanza_acceso_denegado(repo):
    g = repo.sembrar(2)
    with pytest.raises(AccesoDenegadoError):
        svc.obtener_gasto(None, 1, g["id"], repo=repo)


def test_actualizar_completo_reemplaza_los_cuatro_campos(repo):
    g = repo.sembrar(1)
    ayer = date.today() - timedelta(days=1)
    nuevo = svc.actualizar_gasto(
        None, 1, g["id"],
        {"descripcion": "  Cena ", "monto": 30.0, "categoria": "otros", "fecha": ayer}, repo=repo,
    )
    assert (nuevo["descripcion"], nuevo["monto"], nuevo["categoria"], nuevo["fecha"]) == (
        "Cena", 30.0, "otros", ayer,
    )


def test_actualizar_parcial_deja_intactos_los_demas_campos(repo):
    g = repo.sembrar(1, "Almuerzo", 10.0, "comida")
    nuevo = svc.actualizar_gasto(None, 1, g["id"], {"monto": 99.0}, repo=repo)
    assert nuevo["monto"] == 99.0
    assert nuevo["descripcion"] == "Almuerzo" and nuevo["categoria"] == "comida"


def test_actualizar_sin_cambios_lanza_value_error(repo):
    g = repo.sembrar(1)
    with pytest.raises(ValueError):
        svc.actualizar_gasto(None, 1, g["id"], {}, repo=repo)


def test_actualizar_campo_no_editable_lanza_value_error(repo):
    g = repo.sembrar(1)
    with pytest.raises(ValueError):
        svc.actualizar_gasto(None, 1, g["id"], {"usuario_id": 2}, repo=repo)


@pytest.mark.parametrize(
    "cambios, error",
    [
        ({"monto": 0}, ValueError),
        ({"monto": -5}, ValueError),
        ({"descripcion": "   "}, ValueError),
        ({"categoria": "inventada"}, CategoriaInvalidaError),
        ({"fecha": date.today() + timedelta(days=1)}, ValueError),
    ],
)
def test_actualizar_con_resultado_invalido_no_escribe(repo, cambios, error):
    g = repo.sembrar(1, "Almuerzo", 10.0, "comida")
    with pytest.raises(error):
        svc.actualizar_gasto(None, 1, g["id"], cambios, repo=repo)
    assert repo.obtener_por_id(None, g["id"])["monto"] == 10.0


def test_actualizar_ajeno_o_inexistente_no_escribe(repo):
    g = repo.sembrar(2, monto=10.0)
    with pytest.raises(AccesoDenegadoError):
        svc.actualizar_gasto(None, 1, g["id"], {"monto": 99.0}, repo=repo)
    with pytest.raises(GastoNoEncontradoError):
        svc.actualizar_gasto(None, 1, 999, {"monto": 99.0}, repo=repo)
    assert repo.obtener_por_id(None, g["id"])["monto"] == 10.0


def test_eliminar_propio_lo_borra(repo):
    g = repo.sembrar(1)
    svc.eliminar_gasto(None, 1, g["id"], repo=repo)
    assert repo.obtener_por_id(None, g["id"]) is None


def test_eliminar_ajeno_o_inexistente_no_borra(repo):
    g = repo.sembrar(2)
    with pytest.raises(AccesoDenegadoError):
        svc.eliminar_gasto(None, 1, g["id"], repo=repo)
    with pytest.raises(GastoNoEncontradoError):
        svc.eliminar_gasto(None, 1, 999, repo=repo)
    assert repo.obtener_por_id(None, g["id"]) is not None
