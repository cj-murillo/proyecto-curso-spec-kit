import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user, get_gastos_repo
from app.database import get_db
from app.models.usuario import Usuario
from tests.test_gastos import RepositorioFalso

USUARIO_DE_PRUEBA = Usuario(id=1, email="test@ejemplo.com", hashed_password="no-importa")


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO_DE_PRUEBA
    # raise_server_exceptions=False: sin esto, el TestClient re-lanza la excepción
    # en vez de dejar que el exception_handler de la app la convierta en 500.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_crear_gasto_con_repo_falso(client):
    app.dependency_overrides[get_gastos_repo] = lambda: RepositorioFalso()

    response = client.post(
        "/gastos/", json={"descripcion": "Almuerzo", "monto": 12.50, "categoria": "comida"}
    )

    assert response.status_code == 201
    assert response.json()["descripcion"] == "Almuerzo"


def test_listar_gastos_con_paginacion_invalida_devuelve_422(client):
    app.dependency_overrides[get_gastos_repo] = lambda: RepositorioFalso()

    assert client.get("/gastos/?skip=-1").status_code == 422
    assert client.get("/gastos/?limit=0").status_code == 422


class RepositorioRoto:
    """Simula un fallo inesperado del repositorio (ej. la DB se cae a mitad de la request)."""

    def total_por_categoria(self, db, usuario_id, categoria):
        raise RuntimeError("la base de datos no responde")


def test_error_no_controlado_devuelve_500_sin_stacktrace(client):
    app.dependency_overrides[get_gastos_repo] = lambda: RepositorioRoto()

    response = client.post(
        "/gastos/", json={"descripcion": "Falla", "monto": 10.0, "categoria": "comida"}
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno del servidor"}
