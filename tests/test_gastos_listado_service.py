from datetime import date, timedelta

import pytest

from app.services import gastos as svc
from tests.fakes import RepoGastosEnMemoria

HOY = date.today()


@pytest.fixture
def repo():
    return RepoGastosEnMemoria()


class RepoLegadoListar:
    """Doble con la firma exacta de 001: listar(db, usuario_id, skip, limit), sin contar."""

    def __init__(self):
        self.llamadas = []

    def listar(self, db, usuario_id, skip, limit):
        self.llamadas.append((usuario_id, skip, limit))
        return []


def test_listar_sin_filtros_usa_la_forma_legada_de_001():
    repo = RepoLegadoListar()
    svc.listar_gastos(None, 1, 5, 10, repo=repo)
    assert repo.llamadas == [(1, 5, 10)]


def test_listar_con_filtros_los_reenvia_al_repositorio(repo):
    repo.sembrar(1, categoria="comida", monto=10.0)
    repo.sembrar(1, categoria="otros", monto=20.0)
    gastos = svc.listar_gastos(None, 1, repo=repo, categoria="otros", orden="-monto")
    assert [g["categoria"] for g in gastos] == ["otros"]
    assert repo.ultimo_listar == {"orden": "-monto", "categoria": "otros"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"desde": HOY, "hasta": HOY - timedelta(days=1)},
        {"monto_min": 10.0, "monto_max": 5.0},
        {"orden": "otro"},
    ],
)
def test_listar_con_filtros_invalidos_lanza_value_error(repo, kwargs):
    with pytest.raises(ValueError):
        svc.listar_gastos(None, 1, repo=repo, **kwargs)


def test_contar_gastos_devuelve_el_total_filtrado(repo):
    for monto in (10.0, 20.0, 30.0):
        repo.sembrar(1, monto=monto)
    repo.sembrar(2, monto=99.0)
    assert svc.contar_gastos(None, 1, repo=repo) == 3
    assert svc.contar_gastos(None, 1, repo=repo, monto_min=20.0) == 2


def test_contar_gastos_devuelve_none_si_el_repo_no_define_contar():
    assert svc.contar_gastos(None, 1, repo=RepoLegadoListar()) is None


def test_resumen_incluye_siempre_las_cuatro_categorias(repo):
    repo.sembrar(1, monto=100.0, categoria="comida")
    repo.sembrar(1, monto=20.0, categoria="comida")
    repo.sembrar(1, monto=30.0, categoria="transporte")
    repo.sembrar(2, monto=400.0, categoria="comida")  # de otro usuario

    r = svc.resumen_gastos(None, 1, repo=repo)

    por_cat = {c["categoria"]: c for c in r["categorias"]}
    assert set(por_cat) == {"comida", "transporte", "entretenimiento", "otros"}
    assert (por_cat["comida"]["total"], por_cat["comida"]["cantidad"], por_cat["comida"]["disponible"]) == (120.0, 2, 380.0)
    assert (por_cat["otros"]["total"], por_cat["otros"]["cantidad"], por_cat["otros"]["disponible"]) == (0.0, 0, 500.0)
    assert r["total_general"] == 150.0


def test_resumen_con_rango_acota_total_y_cantidad_pero_no_el_disponible(repo):
    repo.sembrar(1, monto=100.0, categoria="comida", fecha=HOY - timedelta(days=40))
    repo.sembrar(1, monto=20.0, categoria="comida", fecha=HOY)

    r = svc.resumen_gastos(None, 1, desde=HOY - timedelta(days=1), hasta=HOY, repo=repo)

    comida = next(c for c in r["categorias"] if c["categoria"] == "comida")
    assert (comida["total"], comida["cantidad"]) == (20.0, 1)
    assert comida["disponible"] == 380.0  # 500 - 120 histórico
    assert r["total_general"] == 20.0


def test_resumen_con_rango_invalido_lanza_value_error(repo):
    with pytest.raises(ValueError):
        svc.resumen_gastos(None, 1, desde=HOY, hasta=HOY - timedelta(days=1), repo=repo)


def test_info_categorias_coincide_con_la_fuente_unica():
    from app.utils.validadores import CATEGORIAS_PERMITIDAS

    info = svc.info_categorias()
    assert set(info["categorias"]) == set(CATEGORIAS_PERMITIDAS)
    assert info["limite_por_categoria"] == 500.0
