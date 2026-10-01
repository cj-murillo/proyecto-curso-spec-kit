from datetime import date, timedelta

import pytest

from app.repositories import gastos as repo
from app.repositories import usuarios as usuarios_repository
from app.services import gastos as svc

HOY = date.today()


@pytest.fixture
def db(SessionLocalDePrueba):
    sesion = SessionLocalDePrueba()
    yield sesion
    sesion.close()


@pytest.fixture
def datos(db):
    a = usuarios_repository.guardar(db, "a@ejemplo.com", "h").id
    b = usuarios_repository.guardar(db, "b@ejemplo.com", "h").id
    # (descripcion, monto, categoria, dias atrás)
    for desc, monto, cat, dias in [
        ("c1", 120.0, "comida", 10),
        ("c2", 50.0, "comida", 5),
        ("t1", 30.0, "transporte", 5),
        ("o1", 80.0, "otros", 1),
        ("c3", 50.0, "comida", 0),
    ]:
        repo.guardar(db, a, desc, monto, cat, HOY - timedelta(days=dias))
    repo.guardar(db, b, "ajeno", 10.0, "comida", HOY)
    return a, b


def test_filtros_combinados_solo_devuelven_gastos_propios(db, datos):
    a, _ = datos
    r = repo.listar(
        db, a, categoria="comida", desde=HOY - timedelta(days=6), hasta=HOY, monto_min=40.0, monto_max=60.0
    )
    assert [g["descripcion"] for g in r] == ["c2", "c3"]
    assert repo.contar(db, a, categoria="comida", desde=HOY - timedelta(days=6), monto_min=40.0, monto_max=60.0) == 2


@pytest.mark.parametrize(
    "orden, esperado",
    [
        (None, ["c1", "c2", "t1", "o1", "c3"]),
        ("fecha", ["c1", "c2", "t1", "o1", "c3"]),
        ("-fecha", ["c3", "o1", "c2", "t1", "c1"]),
        ("monto", ["t1", "c2", "c3", "o1", "c1"]),
        ("-monto", ["c1", "o1", "c2", "c3", "t1"]),
    ],
)
def test_orden_con_desempate_estable_por_id(db, datos, orden, esperado):
    a, _ = datos
    assert [g["descripcion"] for g in repo.listar(db, a, orden=orden)] == esperado


def test_paginacion_estable_y_total_sin_paginar(db, datos):
    a, _ = datos
    pag1 = repo.listar(db, a, skip=0, limit=2, orden="monto")
    pag2 = repo.listar(db, a, skip=2, limit=2, orden="monto")
    vistos = [g["descripcion"] for g in pag1 + pag2]
    assert len(set(vistos)) == 4
    assert repo.contar(db, a) == 5


def test_contar_es_cero_para_usuario_sin_gastos_y_las_listas_vacias_son_listas(db, datos):
    c = usuarios_repository.guardar(db, "c@ejemplo.com", "h").id
    assert repo.contar(db, c) == 0 and repo.listar(db, c) == []


def test_resumen_con_y_sin_rango(db, datos):
    a, _ = datos
    todo = svc.resumen_gastos(db, a, repo=repo)
    por_cat = {c["categoria"]: c for c in todo["categorias"]}
    assert (por_cat["comida"]["total"], por_cat["comida"]["cantidad"]) == (220.0, 3)
    assert por_cat["comida"]["disponible"] == 280.0
    assert (por_cat["entretenimiento"]["total"], por_cat["entretenimiento"]["disponible"]) == (0.0, 500.0)
    assert todo["total_general"] == 330.0

    acotado = svc.resumen_gastos(db, a, desde=HOY - timedelta(days=5), hasta=HOY, repo=repo)
    comida = next(c for c in acotado["categorias"] if c["categoria"] == "comida")
    assert (comida["total"], comida["cantidad"], comida["disponible"]) == (100.0, 2, 280.0)
    assert acotado["total_general"] == 210.0
