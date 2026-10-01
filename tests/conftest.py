import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def pg_engine():
    url = settings.test_database_url
    if not url:
        pytest.fail("Definir TEST_DATABASE_URL (p. ej. .../gastos_test) para correr los tests")
    # Guard de seguridad: los tests hacen drop_all, nunca contra la BD de desarrollo.
    if url == settings.database_url or not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL debe ser distinta de DATABASE_URL y terminar en _test")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def SessionLocalDePrueba(pg_engine):
    """sessionmaker sobre Postgres con el esquema recreado en cada test."""
    Base.metadata.drop_all(pg_engine)
    Base.metadata.create_all(pg_engine)
    return sessionmaker(bind=pg_engine)


@pytest.fixture
def client(SessionLocalDePrueba):
    """TestClient contra Postgres real: get_db se sustituye por sesiones de prueba."""

    def _get_db_override():
        db = SessionLocalDePrueba()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def registrar_y_loguear(client, email="a@ejemplo.com", password="clave12345") -> dict:
    """Registra un usuario, inicia sesion y devuelve los headers Authorization."""
    assert client.post("/usuarios/", json={"email": email, "password": password}).status_code == 201
    login = client.post("/usuarios/token", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
