from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import get_current_user, get_gastos_repo
from app.main import app
from app.models.usuario import Usuario
from tests.fakes import RepoGastosEnMemoria

USUARIO = Usuario(id=1, email="test@ejemplo.com", hashed_password="x")
COMPLETO = {"descripcion": "Cena", "monto": 20.0, "categoria": "otros", "fecha": date.today().isoformat()}


@pytest.fixture
def repo():
    return RepoGastosEnMemoria()


@pytest.fixture
def api(repo):
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    app.dependency_overrides[get_gastos_repo] = lambda: repo
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_propio_200_inexistente_404_ajeno_403(api, repo):
    mio = repo.sembrar(1, "Almuerzo", 12.5)
    ajeno = repo.sembrar(2)
    r = api.get(f"/gastos/{mio['id']}")
    assert r.status_code == 200 and r.json()["descripcion"] == "Almuerzo"
    assert "usuario_id" not in r.json()
    assert api.get("/gastos/999").status_code == 404
    assert api.get(f"/gastos/{ajeno['id']}").status_code == 403


def test_put_completo_200_y_persiste(api, repo):
    g = repo.sembrar(1)
    r = api.put(f"/gastos/{g['id']}", json=COMPLETO)
    assert r.status_code == 200
    assert api.get(f"/gastos/{g['id']}").json()["descripcion"] == "Cena"


@pytest.mark.parametrize("falta", ["descripcion", "monto", "categoria", "fecha"])
def test_put_sin_un_campo_422(api, repo, falta):
    g = repo.sembrar(1)
    cuerpo = {k: v for k, v in COMPLETO.items() if k != falta}
    assert api.put(f"/gastos/{g['id']}", json=cuerpo).status_code == 422


def test_patch_parcial_200_vacio_y_null_422(api, repo):
    g = repo.sembrar(1, "Almuerzo", 10.0)
    r = api.patch(f"/gastos/{g['id']}", json={"monto": 55.5})
    assert r.status_code == 200
    assert r.json()["monto"] == 55.5 and r.json()["descripcion"] == "Almuerzo"
    assert api.patch(f"/gastos/{g['id']}", json={}).status_code == 422
    assert api.patch(f"/gastos/{g['id']}", json={"monto": None}).status_code == 422


@pytest.mark.parametrize("metodo", ["put", "patch"])
@pytest.mark.parametrize("campo", ["usuario_id", "id"])
def test_put_y_patch_rechazan_campos_desconocidos(api, repo, metodo, campo):
    g = repo.sembrar(1)
    cuerpo = ({**COMPLETO} if metodo == "put" else {"monto": 1.0}) | {campo: 9}
    assert getattr(api, metodo)(f"/gastos/{g['id']}", json=cuerpo).status_code == 422


def test_put_con_reglas_de_negocio_invalidas_400(api, repo):
    g = repo.sembrar(1)
    assert api.put(f"/gastos/{g['id']}", json={**COMPLETO, "monto": 0}).status_code == 400
    assert api.put(f"/gastos/{g['id']}", json={**COMPLETO, "categoria": "nada"}).status_code == 400
    futura = (date.today() + timedelta(days=1)).isoformat()
    assert api.put(f"/gastos/{g['id']}", json={**COMPLETO, "fecha": futura}).status_code == 422


def test_put_patch_delete_ajeno_403_e_inexistente_404(api, repo):
    ajeno = repo.sembrar(2, monto=10.0)
    assert api.put(f"/gastos/{ajeno['id']}", json=COMPLETO).status_code == 403
    assert api.patch(f"/gastos/{ajeno['id']}", json={"monto": 1.0}).status_code == 403
    assert api.delete(f"/gastos/{ajeno['id']}").status_code == 403
    assert repo.obtener_por_id(None, ajeno["id"])["monto"] == 10.0
    assert api.put("/gastos/999", json=COMPLETO).status_code == 404
    assert api.patch("/gastos/999", json={"monto": 1.0}).status_code == 404
    assert api.delete("/gastos/999").status_code == 404


def test_delete_204_y_luego_404(api, repo):
    g = repo.sembrar(1)
    r = api.delete(f"/gastos/{g['id']}")
    assert r.status_code == 204 and r.content == b""
    assert api.get(f"/gastos/{g['id']}").status_code == 404


def test_id_no_numerico_422(api):
    assert api.get("/gastos/abc").status_code == 422
