from app.utils.validadores import categoria_valida


def test_categoria_valida_e_invalida():
    assert categoria_valida("comida") is True
    assert categoria_valida("transporte") is True
    assert categoria_valida("entretenimiento") is True
    assert categoria_valida("otros") is True
    assert categoria_valida("categoria-inventada") is False
