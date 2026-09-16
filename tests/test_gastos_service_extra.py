import pytest
from app.services import gastos as gastos_service
from tests.test_gastos import RepositorioFalso


def test_registrar_gasto_descripcion_vacia_lanza_error():
    with pytest.raises(ValueError):
        gastos_service.registrar_gasto(
            None, 1, "   ", 10.0, "comida", repo=RepositorioFalso()
        )


class RepositorioQueRegistraPaginacion:
    """Doble local: observa los argumentos exactos que listar_gastos reenvía
    a repo.listar() -- RepositorioFalso (tests/test_gastos.py) ignora
    usuario_id/skip/limit y no sirve para esta aserción."""

    def __init__(self):
        self.llamadas: list[tuple] = []

    def listar(self, db, usuario_id, skip, limit):
        self.llamadas.append((db, usuario_id, skip, limit))
        return []


def test_listar_gastos_reenvia_paginacion_al_repositorio():
    repo = RepositorioQueRegistraPaginacion()

    gastos_service.listar_gastos(None, 1, skip=2, limit=5, repo=repo)

    assert repo.llamadas == [(None, 1, 2, 5)]
