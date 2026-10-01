import logging
from datetime import date

from app.repositories import gastos as gastos_repository
from app.utils.validadores import CATEGORIAS_PERMITIDAS, categoria_valida

logger = logging.getLogger(__name__)

LIMITE_POR_CATEGORIA = 500.0


class CategoriaInvalidaError(Exception):
    pass


class LimiteExcedidoError(Exception):
    pass


class GastoNoEncontradoError(Exception):
    pass


class AccesoDenegadoError(Exception):
    pass


def _validar_fecha(fecha: date | None) -> None:
    if fecha is not None and fecha > date.today():
        raise ValueError("La fecha no puede ser futura")


def _validar_gasto(
    descripcion: str, monto: float, categoria: str, fecha: date | None = None
) -> None:
    if not descripcion or not descripcion.strip():
        raise ValueError("La descripción no puede estar vacía")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero")
    if not categoria_valida(categoria):
        raise CategoriaInvalidaError(f"'{categoria}' no es una categoría válida")
    _validar_fecha(fecha)


def _bloquear_usuario(repo, db, usuario_id: int) -> None:
    """Serializa por usuario la comprobación del límite + escritura (FR-007). Un repo sin
    `bloquear_usuario` (dobles de 001) simplemente no bloquea."""
    bloquear = getattr(repo, "bloquear_usuario", None)
    if bloquear is not None:
        bloquear(db, usuario_id)


def _verificar_limite(
    db, usuario_id: int, categoria: str, monto: float, repo, excluir_id: int | None = None
) -> None:
    # Contrato 001: sin excluir_id se llama a total_por_categoria con la forma legada.
    extra = {} if excluir_id is None else {"excluir_id": excluir_id}
    total_actual = repo.total_por_categoria(db, usuario_id, categoria, **extra)
    if total_actual + monto > LIMITE_POR_CATEGORIA:
        logger.warning(
            "Gasto rechazado por límite excedido: usuario_id=%s categoria=%s monto=%s",
            usuario_id, categoria, monto,
        )
        raise LimiteExcedidoError(
            f"Este gasto supera el límite de {LIMITE_POR_CATEGORIA} para la categoría '{categoria}'"
        )


def registrar_gasto(
    db,
    usuario_id: int,
    descripcion: str,
    monto: float,
    categoria: str,
    repo=gastos_repository,
    fecha: date | None = None,
) -> dict:
    _validar_gasto(descripcion, monto, categoria, fecha)
    _bloquear_usuario(repo, db, usuario_id)

    _verificar_limite(db, usuario_id, categoria, monto, repo)

    # Contrato 001: sin fecha se llama a guardar con la forma legada.
    extra = {} if fecha is None else {"fecha": fecha}
    gasto = repo.guardar(db, usuario_id, descripcion, monto, categoria, **extra)
    logger.info(
        "Gasto registrado: usuario_id=%s gasto_id=%s categoria=%s",
        usuario_id, gasto["id"], categoria,
    )
    return gasto


def _filtros_informados(**filtros) -> dict:
    return {k: v for k, v in filtros.items() if v is not None}


def _validar_rangos(desde, hasta, monto_min=None, monto_max=None) -> None:
    if desde and hasta and desde > hasta:
        raise ValueError("'desde' no puede ser posterior a 'hasta'")
    if monto_min is not None and monto_max is not None and monto_min > monto_max:
        raise ValueError("'monto_min' no puede ser mayor que 'monto_max'")


ORDENES_VALIDOS = ("fecha", "-fecha", "monto", "-monto")


def listar_gastos(
    db,
    usuario_id: int,
    skip: int = 0,
    limit: int = 20,
    repo=gastos_repository,
    categoria: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
    orden: str | None = None,
) -> list[dict]:
    _validar_rangos(desde, hasta, monto_min, monto_max)
    if orden is not None and orden not in ORDENES_VALIDOS:
        raise ValueError(f"Orden inválido: use uno de {', '.join(ORDENES_VALIDOS)}")
    filtros = _filtros_informados(
        categoria=categoria, desde=desde, hasta=hasta,
        monto_min=monto_min, monto_max=monto_max, orden=orden,
    )
    # Contrato 001: sin filtros se llama a listar con la forma legada.
    return repo.listar(db, usuario_id, skip, limit, **filtros)


def contar_gastos(
    db,
    usuario_id: int,
    repo=gastos_repository,
    categoria: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
) -> int | None:
    """Total sin paginar; None si el repo no define `contar` (dobles de 001)."""
    contar = getattr(repo, "contar", None)
    if contar is None:
        return None
    filtros = _filtros_informados(
        categoria=categoria, desde=desde, hasta=hasta, monto_min=monto_min, monto_max=monto_max
    )
    return contar(db, usuario_id, **filtros)


def resumen_gastos(
    db, usuario_id: int, desde: date | None = None, hasta: date | None = None,
    repo=gastos_repository,
) -> dict:
    """Siempre todas las categorías permitidas. `disponible` usa el total HISTÓRICO."""
    _validar_rangos(desde, hasta)
    en_rango = {f["categoria"]: f for f in repo.resumen_por_categoria(db, usuario_id, desde, hasta)}
    categorias = []
    for categoria in sorted(CATEGORIAS_PERMITIDAS):
        fila = en_rango.get(categoria, {"total": 0.0, "cantidad": 0})
        historico = repo.total_por_categoria(db, usuario_id, categoria)
        categorias.append({
            "categoria": categoria,
            "total": fila["total"],
            "cantidad": fila["cantidad"],
            "disponible": LIMITE_POR_CATEGORIA - historico,
        })
    return {
        "categorias": categorias,
        "total_general": sum(c["total"] for c in categorias),
    }


def info_categorias() -> dict:
    return {
        "categorias": sorted(CATEGORIAS_PERMITIDAS),
        "limite_por_categoria": LIMITE_POR_CATEGORIA,
    }


CAMPOS_EDITABLES = ("descripcion", "monto", "categoria", "fecha")


def _publico(gasto: dict) -> dict:
    return {k: v for k, v in gasto.items() if k != "usuario_id"}


def _cargar_gasto_propio(db, usuario_id: int, gasto_id: int, repo) -> dict:
    """404 si no existe; 403 si es de otro usuario (Art. IV.4 / V.1)."""
    gasto = repo.obtener_por_id(db, gasto_id)
    if gasto is None:
        raise GastoNoEncontradoError(f"El gasto {gasto_id} no existe")
    if gasto["usuario_id"] != usuario_id:
        raise AccesoDenegadoError("El gasto pertenece a otro usuario")
    return gasto


def obtener_gasto(db, usuario_id: int, gasto_id: int, repo=gastos_repository) -> dict:
    return _publico(_cargar_gasto_propio(db, usuario_id, gasto_id, repo))


def actualizar_gasto(
    db, usuario_id: int, gasto_id: int, cambios: dict, repo=gastos_repository
) -> dict:
    """Un solo punto para PUT (4 campos) y PATCH (subconjunto): mezcla, revalida el resultado."""
    desconocidos = set(cambios) - set(CAMPOS_EDITABLES)
    if desconocidos:
        raise ValueError(f"Campos no editables: {', '.join(sorted(desconocidos))}")
    if not cambios:
        raise ValueError("Debe indicar al menos un campo a modificar")

    _bloquear_usuario(repo, db, usuario_id)
    actual = _cargar_gasto_propio(db, usuario_id, gasto_id, repo)
    nuevo = {c: actual.get(c) for c in CAMPOS_EDITABLES} | cambios
    if isinstance(nuevo["descripcion"], str):
        nuevo["descripcion"] = nuevo["descripcion"].strip()
    _validar_gasto(nuevo["descripcion"], nuevo["monto"], nuevo["categoria"], nuevo["fecha"])
    # El gasto editado no cuenta contra sí mismo; el total se evalúa en la categoría resultante.
    _verificar_limite(db, usuario_id, nuevo["categoria"], nuevo["monto"], repo, excluir_id=gasto_id)

    gasto = repo.actualizar(
        db, gasto_id, usuario_id,
        nuevo["descripcion"], nuevo["monto"], nuevo["categoria"], nuevo["fecha"],
    )
    if gasto is None:  # borrado entre la lectura y la escritura
        raise GastoNoEncontradoError(f"El gasto {gasto_id} no existe")
    logger.info("Gasto actualizado: usuario_id=%s gasto_id=%s", usuario_id, gasto_id)
    return gasto


def eliminar_gasto(db, usuario_id: int, gasto_id: int, repo=gastos_repository) -> None:
    _cargar_gasto_propio(db, usuario_id, gasto_id, repo)
    if not repo.eliminar(db, gasto_id, usuario_id):
        raise GastoNoEncontradoError(f"El gasto {gasto_id} no existe")
    logger.info("Gasto eliminado: usuario_id=%s gasto_id=%s", usuario_id, gasto_id)
