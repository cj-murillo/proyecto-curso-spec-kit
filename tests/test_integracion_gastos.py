import pytest
from app.repositories import usuarios as usuarios_repository
from app.repositories import gastos as gastos_repository
from app.services import gastos as gastos_service


@pytest.fixture
def db_session(SessionLocalDePrueba):
    db = SessionLocalDePrueba()
    yield db
    db.close()


def test_registrar_y_listar_gasto_integracion(db_session):
    usuario = usuarios_repository.guardar(db_session, "test@ejemplo.com", "hash-de-prueba")

    gastos_service.registrar_gasto(
        db_session, usuario.id, "Almuerzo", 12.50, "comida", repo=gastos_repository
    )

    gastos = gastos_service.listar_gastos(db_session, usuario.id, repo=gastos_repository)

    assert len(gastos) == 1
    assert gastos[0]["descripcion"] == "Almuerzo"


def test_limite_por_categoria_integracion(db_session):
    usuario = usuarios_repository.guardar(db_session, "otro@ejemplo.com", "hash-de-prueba")

    gastos_service.registrar_gasto(db_session, usuario.id, "Gasto 1", 490.0, "comida", repo=gastos_repository)

    with pytest.raises(gastos_service.LimiteExcedidoError):
        gastos_service.registrar_gasto(db_session, usuario.id, "Gasto 2", 50.0, "comida", repo=gastos_repository)
