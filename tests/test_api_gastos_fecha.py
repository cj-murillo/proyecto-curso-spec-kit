from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import get_current_user, get_gastos_repo
from app.main import app
from app.models.usuario import Usuario

USUARIO = Usuario(id=1, email="test@ejemplo.com", hashed_password="x")
DATOS = {"descripcion": "Almuerzo", "monto": 12.5, "categoria": "comida"}


class RepoEnMemoria:
    def total_por_categoria(self, db, usuario_id, categoria):
        return 0.0

    def guardar(self, db, usuario_id, descripcion, monto, categoria, fecha=None):
        return {
            "id": 1,
            "descripcion": descripcion,
            "monto": monto,
            "categoria": categoria,
            "fecha": fecha or date.today(),
        }


@pytest.fixture
def api():
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    app.dependency_overrides[get_gastos_repo] = lambda: RepoEnMemoria()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_crear_sin_fecha_responde_con_la_fecha_de_hoy(api):
    r = api.post("/gastos/", json=DATOS)
    assert r.status_code == 201
    assert r.json()["fecha"] == date.today().isoformat()


def test_crear_con_fecha_pasada(api):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    r = api.post("/gastos/", json={**DATOS, "fecha": ayer})
    assert r.status_code == 201
    assert r.json()["fecha"] == ayer


def test_crear_con_fecha_futura_devuelve_422(api):
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert api.post("/gastos/", json={**DATOS, "fecha": manana}).status_code == 422


@pytest.mark.parametrize("campo", ["usuario_id", "id"])
def test_crear_ignora_campos_desconocidos_como_en_001(api, campo):
    assert api.post("/gastos/", json={**DATOS, campo: 5}).status_code == 201


def test_monto_con_tres_decimales_o_sobre_el_maximo_devuelve_422(api):
    assert api.post("/gastos/", json={**DATOS, "monto": 1.234}).status_code == 422
    assert api.post("/gastos/", json={**DATOS, "monto": 1_000_001}).status_code == 422


def test_reglas_de_negocio_de_001_siguen_respondiendo_400(api):
    assert api.post("/gastos/", json={**DATOS, "monto": 0}).status_code == 400
    assert api.post("/gastos/", json={**DATOS, "categoria": "inventada"}).status_code == 400
    assert api.post("/gastos/", json={**DATOS, "descripcion": "   "}).status_code == 400
