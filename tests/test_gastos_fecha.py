from datetime import date, timedelta

import pytest

from app.services import gastos as gastos_service


class RepoQueRegistraLlamadas:
    """Doble con la firma legada de 001 + fecha opcional."""

    def __init__(self):
        self.llamadas = []

    def total_por_categoria(self, db, usuario_id, categoria):
        return 0.0

    def guardar(self, db, usuario_id, descripcion, monto, categoria, **extra):
        self.llamadas.append(extra)
        return {"id": 1, "descripcion": descripcion, "monto": monto, "categoria": categoria, **extra}


def test_sin_fecha_llama_a_guardar_con_la_forma_legada():
    repo = RepoQueRegistraLlamadas()

    gastos_service.registrar_gasto(None, 1, "Almuerzo", 10.0, "comida", repo=repo)

    assert repo.llamadas == [{}]


def test_con_fecha_la_envia_al_repositorio():
    repo = RepoQueRegistraLlamadas()
    ayer = date.today() - timedelta(days=1)

    gasto = gastos_service.registrar_gasto(None, 1, "Almuerzo", 10.0, "comida", repo=repo, fecha=ayer)

    assert repo.llamadas == [{"fecha": ayer}]
    assert gasto["fecha"] == ayer


def test_fecha_futura_lanza_error_y_no_guarda():
    repo = RepoQueRegistraLlamadas()
    manana = date.today() + timedelta(days=1)

    with pytest.raises(ValueError):
        gastos_service.registrar_gasto(None, 1, "Almuerzo", 10.0, "comida", repo=repo, fecha=manana)

    assert repo.llamadas == []


def test_fecha_de_hoy_se_acepta():
    repo = RepoQueRegistraLlamadas()
    gastos_service.registrar_gasto(None, 1, "Almuerzo", 10.0, "comida", repo=repo, fecha=date.today())
    assert len(repo.llamadas) == 1
