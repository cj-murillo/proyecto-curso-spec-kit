import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # StaticPool: cada request abre un get_db() nuevo (una conexión nueva);
    # sin StaticPool cada conexión ve una base ":memory:" vacía distinta.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _get_db_override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_registrar_y_login(client):
    response = client.post(
        "/usuarios/", json={"email": "nuevo@ejemplo.com", "password": "clave123"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "nuevo@ejemplo.com"
    assert "password" not in response.json()

    login = client.post(
        "/usuarios/token",
        data={"username": "nuevo@ejemplo.com", "password": "clave123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_registrar_email_duplicado_devuelve_400(client):
    client.post("/usuarios/", json={"email": "dup@ejemplo.com", "password": "clave123"})
    response = client.post(
        "/usuarios/", json={"email": "dup@ejemplo.com", "password": "otra-clave"}
    )
    assert response.status_code == 400


def test_login_credenciales_invalidas_401(client):
    client.post(
        "/usuarios/", json={"email": "test@ejemplo.com", "password": "clave123"}
    )
    response = client.post(
        "/usuarios/token",
        data={"username": "test@ejemplo.com", "password": "clave-incorrecta"},
    )
    assert response.status_code == 401
