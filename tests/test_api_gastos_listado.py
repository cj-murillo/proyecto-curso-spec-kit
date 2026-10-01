from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import get_current_user, get_gastos_repo
from app.main import app
from app.models.usuario import Usuario
from tests.fakes import RepoGastosEnMemoria

USUARIO = Usuario(id=1, email="test@ejemplo.com", hashed_password="x")
HOY = date.today()


class RepoLegado:
    """Firma exacta de 001, sin contar."""

    def __init__(self):
        self.usuario_ids = []

    def listar(self, db, usuario_id, skip=0, limit=20):
        self.usuario_ids.append(usuario_id)
        return []


@pytest.fixture
def repo():
    return RepoGastosEnMemoria()


def _cliente(repo):
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    app.dependency_overrides[get_gastos_repo] = lambda: repo
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api(repo):
    with _cliente(repo) as c:
        yield c
    app.dependency_overrides.clear()


def test_listado_con_filtros_orden_y_total(api, repo):
    for monto in (10.0, 30.0, 20.0):
        repo.sembrar(1, monto=monto, categoria="comida")
    repo.sembrar(1, monto=99.0, categoria="otros")
    repo.sembrar(2, monto=1.0, categoria="comida")

    r = api.get("/gastos/?categoria=comida&orden=-monto&limit=2")

    assert r.status_code == 200
    assert [g["monto"] for g in r.json()] == [30.0, 20.0]
    assert r.headers["X-Total-Count"] == "3"


def test_lista_vacia_devuelve_lista_y_total_cero(api):
    r = api.get("/gastos/")
    assert r.json() == [] and r.headers["X-Total-Count"] == "0"


@pytest.mark.parametrize(
    "query",
    [
        f"desde={HOY}&hasta={HOY - timedelta(days=1)}",
        "monto_min=10&monto_max=5",
        "orden=otro",
        "skip=-1",
        "limit=0",
        "limit=101",
        "desde=no-es-fecha",
    ],
)
def test_parametros_invalidos_devuelven_422(api, query):
    assert api.get(f"/gastos/?{query}").status_code == 422


def test_resumen_y_categorias_no_son_capturadas_por_gasto_id(api, repo):
    repo.sembrar(1, monto=120.0, categoria="comida")
    resumen = api.get("/gastos/resumen")
    categorias = api.get("/gastos/categorias")
    assert resumen.status_code == 200 and len(resumen.json()["categorias"]) == 4
    assert resumen.json()["total_general"] == 120.0
    assert categorias.status_code == 200
    assert categorias.json()["limite_por_categoria"] == 500.0
    assert set(categorias.json()["categorias"]) == {"comida", "transporte", "entretenimiento", "otros"}


def test_resumen_con_rango_invalido_422(api):
    assert api.get(f"/gastos/resumen?desde={HOY}&hasta={HOY - timedelta(days=1)}").status_code == 422


def test_doble_legado_sin_contar_responde_200_sin_header_y_ignora_usuario_id_del_query():
    legado = RepoLegado()
    with _cliente(legado) as c:
        r = c.get("/gastos/?usuario_id=999")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert "X-Total-Count" not in r.headers
    assert legado.usuario_ids == [USUARIO.id]


def test_endpoints_nuevos_exigen_autenticacion(repo):
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_gastos_repo] = lambda: repo
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.get("/gastos/resumen").status_code == 401
        assert c.get("/gastos/categorias").status_code == 401
    app.dependency_overrides.clear()
