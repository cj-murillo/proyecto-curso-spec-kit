import pytest

from app.repositories import gastos as gastos_repository
from tests.conftest import registrar_y_loguear

PASS = "clave12345"


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_perfil_sin_datos_de_password(client):
    h = registrar_y_loguear(client, "ana@ejemplo.com")
    r = client.get("/usuarios/me", headers=h)
    assert r.status_code == 200
    assert set(r.json()) == {"id", "email"} and r.json()["email"] == "ana@ejemplo.com"


def test_perfil_sin_token_401(client):
    assert client.get("/usuarios/me").status_code == 401


def test_cambiar_email_emite_token_nuevo_y_el_anterior_deja_de_valer(client):
    viejo = registrar_y_loguear(client, "ana@ejemplo.com")
    r = client.patch("/usuarios/me", headers=viejo, json={"email": "Nueva@Ejemplo.com", "password_actual": PASS})
    assert r.status_code == 200 and r.json()["email"] == "nueva@ejemplo.com"
    assert client.get("/usuarios/me", headers=_auth(r.json()["access_token"])).json()["email"] == "nueva@ejemplo.com"
    assert client.get("/usuarios/me", headers=viejo).status_code == 401


def test_token_anterior_nunca_opera_como_otro_usuario_que_registra_el_email_viejo(client):
    token_ana = registrar_y_loguear(client, "ana@ejemplo.com")
    client.patch("/usuarios/me", headers=token_ana, json={"email": "ana2@ejemplo.com", "password_actual": PASS})
    registrar_y_loguear(client, "ana@ejemplo.com", "otra-clave-77")  # otra persona toma el email viejo
    assert client.get("/usuarios/me", headers=token_ana).status_code == 401
    assert client.get("/gastos/", headers=token_ana).status_code == 401


def test_cambiar_email_errores(client):
    registrar_y_loguear(client, "otro@ejemplo.com")
    h = registrar_y_loguear(client, "ana@ejemplo.com")
    assert client.patch("/usuarios/me", headers=h, json={"email": "otro@ejemplo.com", "password_actual": PASS}).status_code == 400
    assert client.patch("/usuarios/me", headers=h, json={"email": "x@ejemplo.com", "password_actual": "mala"}).status_code == 400
    assert client.patch("/usuarios/me", headers=h, json={"email": "x@ejemplo.com"}).status_code == 422
    assert client.patch("/usuarios/me", headers=h, json={"email": "no-es-email", "password_actual": PASS}).status_code == 422
    assert client.get("/usuarios/me", headers=h).json()["email"] == "ana@ejemplo.com"


def test_cambiar_password(client):
    h = registrar_y_loguear(client, "ana@ejemplo.com")
    r = client.put("/usuarios/me/password", headers=h, json={"password_actual": PASS, "password_nueva": "nueva-clave-1"})
    assert r.status_code == 204
    assert client.post("/usuarios/token", data={"username": "ana@ejemplo.com", "password": "nueva-clave-1"}).status_code == 200
    assert client.post("/usuarios/token", data={"username": "ana@ejemplo.com", "password": PASS}).status_code == 401


@pytest.mark.parametrize(
    "cuerpo, codigo",
    [
        ({"password_actual": "mala", "password_nueva": "nueva-clave-1"}, 400),
        ({"password_actual": PASS, "password_nueva": PASS}, 400),
        ({"password_actual": PASS, "password_nueva": "corta"}, 422),
        ({"password_actual": PASS, "password_nueva": "x" * 73}, 422),
        ({"password_actual": PASS}, 422),
    ],
)
def test_cambiar_password_errores_no_cambian_nada(client, cuerpo, codigo):
    h = registrar_y_loguear(client, "ana@ejemplo.com")
    assert client.put("/usuarios/me/password", headers=h, json=cuerpo).status_code == codigo
    assert client.post("/usuarios/token", data={"username": "ana@ejemplo.com", "password": PASS}).status_code == 200


def test_eliminar_cuenta(client, SessionLocalDePrueba):
    h = registrar_y_loguear(client, "ana@ejemplo.com")
    client.post("/gastos/", headers=h, json={"descripcion": "x", "monto": 5.0, "categoria": "comida"})

    assert client.request("DELETE", "/usuarios/me", headers=h, json={"password_actual": "mala"}).status_code == 400
    assert client.request("DELETE", "/usuarios/me", headers=h).status_code == 422
    assert client.get("/usuarios/me", headers=h).status_code == 200

    assert client.request("DELETE", "/usuarios/me", headers=h, json={"password_actual": PASS}).status_code == 204
    assert client.get("/usuarios/me", headers=h).status_code == 401
    db = SessionLocalDePrueba()
    try:
        assert gastos_repository.contar(db, 1) == 0
    finally:
        db.close()


def test_registro_valida_password_y_normaliza_email(client):
    for password in ("corta", "x" * 73):
        assert client.post("/usuarios/", json={"email": "a@ejemplo.com", "password": password}).status_code == 422
    r = client.post("/usuarios/", json={"email": "Nuevo@Ejemplo.COM", "password": PASS})
    assert r.status_code == 201 and r.json()["email"] == "nuevo@ejemplo.com"
    assert client.post("/usuarios/token", data={"username": "NUEVO@ejemplo.com", "password": PASS}).status_code == 200
