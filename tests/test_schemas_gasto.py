from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.gasto import GastoCreate

BASE = {"descripcion": "Almuerzo", "monto": 12.5, "categoria": "comida"}


def test_descripcion_se_normaliza_sin_espacios_en_los_extremos():
    assert GastoCreate(**{**BASE, "descripcion": "  Almuerzo  "}).descripcion == "Almuerzo"


def test_descripcion_mayor_a_200_caracteres_es_invalida():
    GastoCreate(**{**BASE, "descripcion": "a" * 200})
    with pytest.raises(ValidationError):
        GastoCreate(**{**BASE, "descripcion": "a" * 201})


@pytest.mark.parametrize("monto", [12.345, 0.001, 1_000_000.01])
def test_monto_con_mas_de_dos_decimales_o_sobre_el_maximo_es_invalido(monto):
    with pytest.raises(ValidationError):
        GastoCreate(**{**BASE, "monto": monto})


@pytest.mark.parametrize("monto", [12.5, 0.01, 1_000_000, 100])
def test_monto_valido(monto):
    assert GastoCreate(**{**BASE, "monto": monto}).monto == monto


def test_fecha_futura_es_invalida_y_hoy_o_pasada_son_validas():
    GastoCreate(**{**BASE, "fecha": date.today()})
    GastoCreate(**{**BASE, "fecha": date.today() - timedelta(days=30)})
    with pytest.raises(ValidationError):
        GastoCreate(**{**BASE, "fecha": date.today() + timedelta(days=1)})


@pytest.mark.parametrize("campo", ["usuario_id", "id", "otro"])
def test_create_ignora_campos_desconocidos_como_en_001(campo):
    gasto = GastoCreate(**{**BASE, campo: 1})
    assert not hasattr(gasto, campo)
