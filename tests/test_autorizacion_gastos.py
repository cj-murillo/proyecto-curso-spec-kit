from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user, get_gastos_repo
from app.database import get_db
from app.models.usuario import Usuario

USUARIO_DE_PRUEBA = Usuario(id=1, email="test@ejemplo.com", hashed_password="no-importa")


class RepositorioQueRegistraUsuarioId:
    """Test double que expone qué usuario_id recibió guardar(), para probar
    que el router nunca usa un usuario_id que venga del body."""

    def __init__(self):
        self.usuario_ids_recibidos: list[int] = []

    def guardar(self, db, usuario_id, descripcion, monto, categoria):
        self.usuario_ids_recibidos.append(usuario_id)
        return {"id": 1, "descripcion": descripcion, "monto": monto, "categoria": categoria}

    def listar(self, db, usuario_id, skip=0, limit=20):
        self.usuario_ids_recibidos.append(usuario_id)
        return []

    def total_por_categoria(self, db, usuario_id, categoria):
        return 0.0


def test_listar_gastos_sin_token_devuelve_401():
    # Sin overrides de get_current_user: el oauth2_scheme real exige un
    # header Authorization y, sin él, FastAPI responde 401 antes de llegar
    # al router (caso de error 4 de spec.md).
    app.dependency_overrides[get_db] = lambda: None
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/gastos/")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_crear_gasto_sin_token_devuelve_401():
    # Caso de error 4 de spec.md, mitad "registrar": POST /gastos/ sin
    # Authorization también debe dar 401 antes de tocar el service.
    app.dependency_overrides[get_db] = lambda: None
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/gastos/",
                json={"descripcion": "Almuerzo", "monto": 12.50, "categoria": "comida"},
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_listar_gastos_ignora_usuario_id_del_query():
    # Caso de error 5 de spec.md, mitad "listar": un usuario_id ajeno en el
    # query param nunca se usa para filtrar -- siempre se usa el del token.
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO_DE_PRUEBA
    repo = RepositorioQueRegistraUsuarioId()
    app.dependency_overrides[get_gastos_repo] = lambda: repo
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/gastos/?usuario_id=999")
        assert response.status_code == 200
        assert repo.usuario_ids_recibidos == [USUARIO_DE_PRUEBA.id]
    finally:
        app.dependency_overrides.clear()


def test_crear_gasto_ignora_usuario_id_del_body():
    # Caso de error 5 de spec.md: pasar un usuario_id ajeno en el body no
    # tiene efecto -- GastoCreate no declara ese campo, así que Pydantic lo
    # descarta y el service usa siempre el usuario_id del token decodificado.
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: USUARIO_DE_PRUEBA
    repo = RepositorioQueRegistraUsuarioId()
    app.dependency_overrides[get_gastos_repo] = lambda: repo
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/gastos/",
                json={
                    "descripcion": "Almuerzo",
                    "monto": 12.50,
                    "categoria": "comida",
                    "usuario_id": 999,
                },
            )
        assert response.status_code == 201
        assert repo.usuario_ids_recibidos == [USUARIO_DE_PRUEBA.id]
    finally:
        app.dependency_overrides.clear()
