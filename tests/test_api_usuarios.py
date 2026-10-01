def test_registrar_y_login(client):
    response = client.post(
        "/usuarios/", json={"email": "nuevo@ejemplo.com", "password": "clave12345"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "nuevo@ejemplo.com"
    assert "password" not in response.json()

    login = client.post(
        "/usuarios/token",
        data={"username": "nuevo@ejemplo.com", "password": "clave12345"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_registrar_email_duplicado_devuelve_400(client):
    client.post("/usuarios/", json={"email": "dup@ejemplo.com", "password": "clave12345"})
    response = client.post(
        "/usuarios/", json={"email": "dup@ejemplo.com", "password": "otra-clave-1"}
    )
    assert response.status_code == 400


def test_login_credenciales_invalidas_401(client):
    client.post("/usuarios/", json={"email": "test@ejemplo.com", "password": "clave12345"})
    response = client.post(
        "/usuarios/token",
        data={"username": "test@ejemplo.com", "password": "clave-incorrecta"},
    )
    assert response.status_code == 401
