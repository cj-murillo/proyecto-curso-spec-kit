import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.mcp.auth import JWTTokenVerifier
from app.mcp.tools import gastos as mcp_gastos
from app.security import crear_access_token


class _AccessTokenFalso:
    def __init__(self, subject):
        self.subject = subject


@pytest.fixture
def db_en_memoria(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocalDePrueba = sessionmaker(bind=engine)
    monkeypatch.setattr(mcp_gastos, "SessionLocal", SessionLocalDePrueba)
    return SessionLocalDePrueba


def test_registrar_gasto_exitoso(db_en_memoria, monkeypatch):
    # Sin token (stdio): cae al usuario demo, documentado como simplificación
    # consciente en el propio código (Artículo VI.4).
    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: None)

    resultado = mcp_gastos.registrar_gasto("Almuerzo", 12.50, "comida")

    assert resultado["descripcion"] == "Almuerzo"
    assert "error" not in resultado


def test_registrar_gasto_categoria_invalida_retorna_error_estructurado(db_en_memoria, monkeypatch):
    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: None)

    resultado = mcp_gastos.registrar_gasto("Cine", 20.0, "categoria-inventada")

    assert "error" in resultado


def test_registrar_gasto_usa_identidad_del_token_verificado(db_en_memoria, monkeypatch):
    # Con token verificado, la identidad sale del token, nunca del usuario
    # demo -- corrige el bug del proyecto de referencia (Artículo VI.4).
    db = db_en_memoria()
    from app.repositories import usuarios as usuarios_repository
    from app.security import hash_password

    usuario = usuarios_repository.guardar(db, "real@ejemplo.com", hash_password("x"))
    db.close()

    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: _AccessTokenFalso("real@ejemplo.com"))

    resultado = mcp_gastos.registrar_gasto("Cena", 15.0, "comida")

    assert resultado["descripcion"] == "Cena"
    # No se creó ningún usuario demo adicional: solo existe el "real".
    db2 = db_en_memoria()
    assert usuarios_repository.obtener_por_email(db2, "demo@curso.com") is None
    db2.close()


def test_listar_gastos_exitoso(db_en_memoria, monkeypatch):
    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: None)

    mcp_gastos.registrar_gasto("Almuerzo", 12.50, "comida")
    gastos = mcp_gastos.listar_gastos()

    assert len(gastos) == 1
    assert gastos[0]["descripcion"] == "Almuerzo"


def test_listar_gastos_token_sin_usuario_retorna_error_estructurado(db_en_memoria, monkeypatch):
    # Token verificado pero cuyo subject no corresponde a ningún usuario
    # registrado (Artículo VI.3: error de negocio, nunca excepción sin controlar).
    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: _AccessTokenFalso("fantasma@ejemplo.com"))

    resultado = mcp_gastos.listar_gastos()

    assert "error" in resultado


def test_verifier_acepta_token_valido():
    token = crear_access_token({"sub": "test@ejemplo.com"})
    verifier = JWTTokenVerifier()

    access_token = asyncio.run(verifier.verify_token(token))

    assert access_token is not None
    assert access_token.subject == "test@ejemplo.com"


def test_verifier_rechaza_token_invalido():
    verifier = JWTTokenVerifier()

    access_token = asyncio.run(verifier.verify_token("token-basura-no-es-jwt"))

    assert access_token is None
