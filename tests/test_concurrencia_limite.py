"""El límite de 500 por categoría no se supera aunque las peticiones lleguen a la vez (FR-007).

Postgres real, sesiones propias por hilo, sin unittest.mock. El repo "lento" agranda la ventana
de carrera entre leer el total y escribir: sin el bloqueo por usuario estas pruebas fallarían."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.repositories import gastos as gastos_repository
from app.repositories import usuarios as usuarios_repository
from app.services import gastos as svc
from app.services.gastos import LimiteExcedidoError


class RepoLento:
    def __getattr__(self, nombre):
        return getattr(gastos_repository, nombre)

    def total_por_categoria(self, *args, **kwargs):
        total = gastos_repository.total_por_categoria(*args, **kwargs)
        time.sleep(0.3)
        return total


@pytest.fixture
def escenario(SessionLocalDePrueba):
    db = SessionLocalDePrueba()
    uid = usuarios_repository.guardar(db, "conc@ejemplo.com", "h").id
    editable = gastos_repository.guardar(db, uid, "editable", 100.0, "comida")
    gastos_repository.guardar(db, uid, "resto", 300.0, "comida")  # total 400
    db.close()
    return SessionLocalDePrueba, uid, editable["id"]


def _correr_a_la_vez(SessionLocal, operaciones):
    barrera = threading.Barrier(len(operaciones))
    resultados = []

    def ejecutar(operacion):
        db = SessionLocal()
        try:
            barrera.wait()
            operacion(db)
            return "ok"
        except LimiteExcedidoError:
            return "limite"
        finally:
            db.close()

    with ThreadPoolExecutor(len(operaciones)) as pool:
        resultados = list(pool.map(ejecutar, operaciones))
    return resultados


def _total(SessionLocal, usuario_id):
    db = SessionLocal()
    try:
        return gastos_repository.total_por_categoria(db, usuario_id, "comida")
    finally:
        db.close()


def test_dos_altas_simultaneas_de_60_solo_una_entra(escenario):
    SessionLocal, uid, _ = escenario
    alta = lambda db: svc.registrar_gasto(db, uid, "x", 60.0, "comida", repo=RepoLento())

    resultados = _correr_a_la_vez(SessionLocal, [alta, alta])

    assert sorted(resultados) == ["limite", "ok"]
    assert _total(SessionLocal, uid) == 460.0


def test_una_edicion_y_un_alta_simultaneas_respetan_el_limite(escenario):
    SessionLocal, uid, gid = escenario
    alta = lambda db: svc.registrar_gasto(db, uid, "x", 60.0, "comida", repo=RepoLento())
    edicion = lambda db: svc.actualizar_gasto(db, uid, gid, {"monto": 160.0}, repo=RepoLento())

    resultados = _correr_a_la_vez(SessionLocal, [alta, edicion])

    assert sorted(resultados) == ["limite", "ok"]
    assert _total(SessionLocal, uid) <= 500.0


def test_dos_ediciones_simultaneas_del_mismo_gasto_no_se_mezclan(escenario):
    SessionLocal, uid, gid = escenario
    a = lambda db: svc.actualizar_gasto(
        db, uid, gid, {"monto": 120.0, "descripcion": "A"}, repo=RepoLento()
    )
    b = lambda db: svc.actualizar_gasto(
        db, uid, gid, {"monto": 130.0, "descripcion": "B"}, repo=RepoLento()
    )

    assert _correr_a_la_vez(SessionLocal, [a, b]) == ["ok", "ok"]

    db = SessionLocal()
    try:
        final = gastos_repository.obtener_por_id(db, gid)
    finally:
        db.close()
    assert (final["descripcion"], final["monto"]) in {("A", 120.0), ("B", 130.0)}
    assert _total(SessionLocal, uid) <= 500.0
