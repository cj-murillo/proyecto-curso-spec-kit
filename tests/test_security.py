import time
import pytest
import jwt

from app.security import (
    hash_password,
    verify_password,
    crear_access_token,
    decodificar_token,
    ALGORITHM,
)
from app.config import settings


def test_hash_y_verify():
    hashed = hash_password("mi-clave-secreta")
    assert hashed != "mi-clave-secreta"
    assert verify_password("mi-clave-secreta", hashed) is True
    assert verify_password("clave-incorrecta", hashed) is False


def test_hash_nuevo_es_argon2():
    assert hash_password("x").startswith("$argon2id$")


@pytest.mark.parametrize(
    "hash_ajeno",
    ["$2b$12$abcdefghijklmnopqrstuuJ5n7r5Q6Vh2b8Ea9Yy3dE0pC1aZ0eqK", "!bcrypt-invalidado"],
)
def test_verify_password_hash_de_otro_esquema_es_falso(hash_ajeno):
    assert verify_password("clave", hash_ajeno) is False


def test_token_expira():
    # Se firma un token ya expirado (exp en el pasado) para no depender de
    # esperar los minutos reales configurados.
    payload = {"sub": "test@ejemplo.com", "exp": int(time.time()) - 10}
    token_expirado = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        decodificar_token(token_expirado)


def test_crear_access_token_decodifica_email():
    token = crear_access_token({"sub": "usuario@ejemplo.com"})
    payload = decodificar_token(token)
    assert payload["sub"] == "usuario@ejemplo.com"
    assert "exp" in payload
