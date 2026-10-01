import pytest

from app.services import gastos as svc
from app.services.gastos import LimiteExcedidoError
from tests.fakes import RepoGastosEnMemoria


@pytest.fixture
def repo():
    return RepoGastosEnMemoria()


def test_editar_hacia_arriba_respeta_el_limite_sin_contarse_a_si_mismo(repo):
    g = repo.sembrar(1, monto=100.0, categoria="comida")
    repo.sembrar(1, monto=300.0, categoria="comida")  # total 400

    svc.actualizar_gasto(None, 1, g["id"], {"monto": 150.0}, repo=repo)  # total 450: ok
    with pytest.raises(LimiteExcedidoError):
        svc.actualizar_gasto(None, 1, g["id"], {"monto": 250.0}, repo=repo)  # total 550

    assert repo.obtener_por_id(None, g["id"])["monto"] == 150.0


def test_mover_a_otra_categoria_evalua_la_categoria_resultante(repo):
    repo.sembrar(1, monto=450.0, categoria="comida")
    g = repo.sembrar(1, monto=100.0, categoria="transporte")

    with pytest.raises(LimiteExcedidoError):
        svc.actualizar_gasto(None, 1, g["id"], {"categoria": "comida"}, repo=repo)

    assert repo.obtener_por_id(None, g["id"])["categoria"] == "transporte"


def test_guardar_el_mismo_gasto_sin_cambios_no_se_rechaza_por_contarse_a_si_mismo(repo):
    g = repo.sembrar(1, monto=500.0, categoria="comida")  # exactamente en el límite
    svc.actualizar_gasto(None, 1, g["id"], {"monto": 500.0}, repo=repo)


def test_limite_exacto_se_acepta_y_un_centavo_mas_se_rechaza(repo):
    g = repo.sembrar(1, monto=100.0, categoria="comida")
    repo.sembrar(1, monto=300.0, categoria="comida")
    svc.actualizar_gasto(None, 1, g["id"], {"monto": 200.0}, repo=repo)  # 500
    with pytest.raises(LimiteExcedidoError):
        svc.actualizar_gasto(None, 1, g["id"], {"monto": 200.01}, repo=repo)


def test_el_limite_es_por_usuario(repo):
    repo.sembrar(2, monto=450.0, categoria="comida")
    g = repo.sembrar(1, monto=10.0, categoria="comida")
    svc.actualizar_gasto(None, 1, g["id"], {"monto": 400.0}, repo=repo)


def test_bloquea_al_usuario_antes_de_leer_el_total_en_alta_y_edicion(repo):
    orden = []
    original = repo.total_por_categoria
    repo.bloquear_usuario = lambda db, uid: orden.append(("bloqueo", uid))
    repo.total_por_categoria = lambda *a, **k: (orden.append(("total",)), original(*a, **k))[1]

    svc.registrar_gasto(None, 1, "x", 10.0, "comida", repo=repo)
    g = repo.sembrar(1)
    svc.actualizar_gasto(None, 1, g["id"], {"monto": 20.0}, repo=repo)

    assert orden[0] == ("bloqueo", 1) and orden[1] == ("total",)
    assert orden[2] == ("bloqueo", 1) and orden[3] == ("total",)


class RepoLegado:
    """Doble con las firmas exactas de 001: sin bloquear_usuario ni excluir_id."""

    def __init__(self):
        self.guardados = 0

    def total_por_categoria(self, db, usuario_id, categoria):
        return 0.0

    def guardar(self, db, usuario_id, descripcion, monto, categoria):
        self.guardados += 1
        return {"id": 1, "descripcion": descripcion, "monto": monto, "categoria": categoria}


def test_repo_legado_sin_bloqueo_ni_excluir_id_sigue_funcionando():
    repo = RepoLegado()
    svc.registrar_gasto(None, 1, "x", 10.0, "comida", repo=repo)
    assert repo.guardados == 1
