import jwt

from app.config import settings
from app.security import ALGORITHM, crear_access_token

from tests.conftest import registrar_y_loguear


def test_token_valido_con_uid_accede(client):
    headers = registrar_y_loguear(client)
    assert client.get("/gastos/", headers=headers).status_code == 200


def test_token_legado_sin_uid_devuelve_401(client):
    registrar_y_loguear(client, "legado@ejemplo.com")
    token = jwt.encode(
        {"sub": "legado@ejemplo.com", "exp": 9999999999}, settings.secret_key, algorithm=ALGORITHM
    )
    assert client.get("/gastos/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_con_uid_ajeno_devuelve_401(client):
    registrar_y_loguear(client, "uno@ejemplo.com")
    token = crear_access_token({"sub": "uno@ejemplo.com", "uid": 99999})
    assert client.get("/gastos/", headers={"Authorization": f"Bearer {token}"}).status_code == 401
