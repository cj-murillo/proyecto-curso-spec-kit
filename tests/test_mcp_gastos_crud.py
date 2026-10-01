"""Tools MCP nuevas y ampliadas: ≥2 pruebas por tool (éxito + error de negocio), Art. VII.6.
Llamadas directas a las funciones (el lifespan de main.py impide probar /mcp por HTTP)."""
import asyncio
from datetime import date, timedelta

import pytest

from app.mcp.tools import gastos as mcp_gastos
from app.repositories import gastos as gastos_repository
from app.repositories import usuarios as usuarios_repository


@pytest.fixture
def db_pruebas(SessionLocalDePrueba, monkeypatch):
    monkeypatch.setattr(mcp_gastos, "SessionLocal", SessionLocalDePrueba)
    monkeypatch.setattr(mcp_gastos, "get_access_token", lambda: None)  # stdio: usuario demo
    return SessionLocalDePrueba


@pytest.fixture
def ajeno(db_pruebas):
    """Un gasto de otro usuario."""
    db = db_pruebas()
    otro = usuarios_repository.guardar(db, "otro@ejemplo.com", "h").id
    gasto = gastos_repository.guardar(db, otro, "ajeno", 10.0, "comida")
    db.close()
    return gasto["id"]


def test_registrar_gasto_con_fecha_devuelve_fecha_iso(db_pruebas):
    r = mcp_gastos.registrar_gasto("Cine", 20.0, "entretenimiento", "2026-01-15")
    assert r["fecha"] == "2026-01-15"


def test_registrar_gasto_con_fecha_futura_o_mal_formada_devuelve_error(db_pruebas):
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert "error" in mcp_gastos.registrar_gasto("x", 1.0, "comida", manana)
    assert "error" in mcp_gastos.registrar_gasto("x", 1.0, "comida", "15/01/2026")


def test_obtener_gasto_exitoso(db_pruebas):
    g = mcp_gastos.registrar_gasto("Almuerzo", 12.5, "comida")
    r = mcp_gastos.obtener_gasto(g["id"])
    assert r["descripcion"] == "Almuerzo" and r["fecha"] == date.today().isoformat()


def test_obtener_gasto_ajeno_o_inexistente_devuelve_error(db_pruebas, ajeno):
    assert "error" in mcp_gastos.obtener_gasto(ajeno)
    assert "error" in mcp_gastos.obtener_gasto(99999)


def test_actualizar_gasto_parcial_exitoso(db_pruebas):
    g = mcp_gastos.registrar_gasto("Almuerzo", 12.5, "comida")
    r = mcp_gastos.actualizar_gasto(g["id"], monto=40.0)
    assert r["monto"] == 40.0 and r["descripcion"] == "Almuerzo"


def test_actualizar_gasto_errores_no_cambian_nada(db_pruebas, ajeno):
    g = mcp_gastos.registrar_gasto("Almuerzo", 400.0, "comida")
    assert "error" in mcp_gastos.actualizar_gasto(g["id"])  # sin campos
    assert "error" in mcp_gastos.actualizar_gasto(g["id"], monto=600.0)  # límite
    assert "error" in mcp_gastos.actualizar_gasto(g["id"], categoria="inventada")
    assert "error" in mcp_gastos.actualizar_gasto(g["id"], fecha="mal")
    assert "error" in mcp_gastos.actualizar_gasto(ajeno, monto=1.0)
    assert mcp_gastos.obtener_gasto(g["id"])["monto"] == 400.0


def test_eliminar_gasto_sin_confirmar_no_borra(db_pruebas):
    g = mcp_gastos.registrar_gasto("Almuerzo", 12.5, "comida")
    assert "error" in mcp_gastos.eliminar_gasto(g["id"])
    assert "error" in mcp_gastos.eliminar_gasto(g["id"], confirmar=False)
    assert mcp_gastos.obtener_gasto(g["id"])["id"] == g["id"]


def test_eliminar_gasto_confirmado_lo_borra(db_pruebas):
    g = mcp_gastos.registrar_gasto("Almuerzo", 12.5, "comida")
    assert mcp_gastos.eliminar_gasto(g["id"], confirmar=True) == {"eliminado": True, "id": g["id"]}
    assert "error" in mcp_gastos.obtener_gasto(g["id"])


def test_eliminar_gasto_ajeno_o_inexistente_devuelve_error_aun_confirmado(db_pruebas, ajeno):
    assert "error" in mcp_gastos.eliminar_gasto(ajeno, confirmar=True)
    assert "error" in mcp_gastos.eliminar_gasto(99999, confirmar=True)


def test_resumen_gastos_exitoso_con_las_cuatro_categorias(db_pruebas):
    mcp_gastos.registrar_gasto("a", 120.0, "comida")
    mcp_gastos.registrar_gasto("b", 30.0, "transporte")
    r = mcp_gastos.resumen_gastos()
    assert len(r["categorias"]) == 4 and r["total_general"] == 150.0


def test_resumen_gastos_con_rango_invalido_devuelve_error(db_pruebas):
    assert "error" in mcp_gastos.resumen_gastos(desde="2026-02-01", hasta="2026-01-01")
    assert "error" in mcp_gastos.resumen_gastos(desde="no-es-fecha")


def test_listar_categorias(db_pruebas):
    r = mcp_gastos.listar_categorias()
    assert set(r["categorias"]) == {"comida", "transporte", "entretenimiento", "otros"}
    assert r["limite_por_categoria"] == 500.0


def test_listar_gastos_con_filtros_y_orden_solo_devuelve_propios(db_pruebas, ajeno):
    mcp_gastos.registrar_gasto("a", 10.0, "comida")
    mcp_gastos.registrar_gasto("b", 30.0, "comida")
    mcp_gastos.registrar_gasto("c", 99.0, "otros")
    r = mcp_gastos.listar_gastos(categoria="comida", orden="-monto")
    assert [g["monto"] for g in r] == [30.0, 10.0]
    assert all(isinstance(g["fecha"], str) for g in r)


def test_listar_gastos_con_filtros_invalidos_devuelve_error(db_pruebas):
    assert "error" in mcp_gastos.listar_gastos(orden="otro")
    assert "error" in mcp_gastos.listar_gastos(desde="2026-02-01", hasta="2026-01-01")


def test_el_servidor_registra_las_siete_tools():
    from app.mcp.server import mcp

    nombres = {t.name for t in asyncio.run(mcp.list_tools())}
    assert nombres == {
        "registrar_gasto", "listar_gastos", "obtener_gasto", "actualizar_gasto",
        "eliminar_gasto", "resumen_gastos", "listar_categorias",
    }
