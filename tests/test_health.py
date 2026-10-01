import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app
from app.repositories import salud as salud_repository
from app.routers.health import get_salud_repo
from app.services import salud as salud_service


class RepoSano:
    def base_disponible(self, db):
        return True


class RepoCaido:
    def base_disponible(self, db):
        return False


class SesionQueFalla:
    def execute(self, *args, **kwargs):
        raise OperationalError("select 1", {}, Exception("base caída"))


def test_servicio_estado_ok_y_degradado():
    assert salud_service.estado(None, repo=RepoSano()) == {"status": "ok", "db": "ok"}
    assert salud_service.estado(None, repo=RepoCaido()) == {"status": "degraded", "db": "error"}


def test_repositorio_real_contra_postgres_devuelve_true(SessionLocalDePrueba):
    db = SessionLocalDePrueba()
    try:
        assert salud_repository.base_disponible(db) is True
    finally:
        db.close()


def test_repositorio_devuelve_false_si_la_base_falla():
    assert salud_repository.base_disponible(SesionQueFalla()) is False


@pytest.fixture
def api(client):
    return client


def test_health_200_sin_autenticacion(api):
    r = api.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok"}


def test_health_503_si_la_base_falla_y_no_un_500_generico(SessionLocalDePrueba):
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_salud_repo] = lambda: RepoCaido()
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": "error"}
