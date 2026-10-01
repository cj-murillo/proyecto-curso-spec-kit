from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.models.gasto import Gasto
from app.models.usuario import Usuario


def _a_dict(g: Gasto) -> dict:
    return {
        "id": g.id,
        "descripcion": g.descripcion,
        "monto": g.monto,
        "categoria": g.categoria,
        "fecha": g.fecha,
    }


def guardar(
    db: Session,
    usuario_id: int,
    descripcion: str,
    monto: float,
    categoria: str,
    fecha: date | None = None,
) -> dict:
    extra = {} if fecha is None else {"fecha": fecha}
    gasto = Gasto(
        usuario_id=usuario_id,
        descripcion=descripcion,
        monto=monto,
        categoria=categoria,
        **extra,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return _a_dict(gasto)


def obtener_por_id(db: Session, gasto_id: int) -> dict | None:
    """Única lectura sin filtro de dueño (Art. III.3): el service compara el dueño antes de exponer."""
    gasto = db.scalars(
        select(Gasto).where(Gasto.id == gasto_id).execution_options(populate_existing=True)
    ).first()
    if gasto is None:
        return None
    return {**_a_dict(gasto), "usuario_id": gasto.usuario_id}


def _propio(db: Session, gasto_id: int, usuario_id: int) -> Gasto | None:
    return db.scalars(
        select(Gasto).where(Gasto.id == gasto_id, Gasto.usuario_id == usuario_id)
    ).first()


def actualizar(
    db: Session,
    gasto_id: int,
    usuario_id: int,
    descripcion: str,
    monto: float,
    categoria: str,
    fecha: date,
) -> dict | None:
    gasto = _propio(db, gasto_id, usuario_id)
    if gasto is None:
        return None
    gasto.descripcion = descripcion
    gasto.monto = monto
    gasto.categoria = categoria
    gasto.fecha = fecha
    db.commit()
    db.refresh(gasto)
    return _a_dict(gasto)


def eliminar(db: Session, gasto_id: int, usuario_id: int) -> bool:
    gasto = _propio(db, gasto_id, usuario_id)
    if gasto is None:
        return False
    db.delete(gasto)
    db.commit()
    return True


def _con_filtros(consulta, usuario_id, categoria, desde, hasta, monto_min, monto_max):
    consulta = consulta.where(Gasto.usuario_id == usuario_id)
    if categoria is not None:
        consulta = consulta.where(Gasto.categoria == categoria)
    if desde is not None:
        consulta = consulta.where(Gasto.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(Gasto.fecha <= hasta)
    if monto_min is not None:
        consulta = consulta.where(Gasto.monto >= monto_min)
    if monto_max is not None:
        consulta = consulta.where(Gasto.monto <= monto_max)
    return consulta


_ORDENES = {
    "fecha": Gasto.fecha.asc(),
    "-fecha": Gasto.fecha.desc(),
    "monto": Gasto.monto.asc(),
    "-monto": Gasto.monto.desc(),
}


def listar(
    db: Session,
    usuario_id: int,
    skip: int = 0,
    limit: int = 20,
    categoria: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
    orden: str | None = None,
) -> list[dict]:
    consulta = _con_filtros(
        select(Gasto), usuario_id, categoria, desde, hasta, monto_min, monto_max
    )
    # Gasto.id ascendente es el orden por defecto y el desempate: paginación estable.
    criterios = [_ORDENES[orden], Gasto.id.asc()] if orden else [Gasto.id.asc()]
    gastos = db.scalars(consulta.order_by(*criterios).offset(skip).limit(limit)).all()
    return [_a_dict(g) for g in gastos]


def contar(
    db: Session,
    usuario_id: int,
    categoria: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    monto_min: float | None = None,
    monto_max: float | None = None,
) -> int:
    consulta = _con_filtros(
        select(func.count(Gasto.id)), usuario_id, categoria, desde, hasta, monto_min, monto_max
    )
    return db.scalar(consulta) or 0


def resumen_por_categoria(
    db: Session, usuario_id: int, desde: date | None = None, hasta: date | None = None
) -> list[dict]:
    consulta = _con_filtros(
        select(Gasto.categoria, func.sum(Gasto.monto), func.count(Gasto.id)),
        usuario_id, None, desde, hasta, None, None,
    ).group_by(Gasto.categoria)
    return [
        {"categoria": c, "total": float(t or 0.0), "cantidad": int(n)}
        for c, t, n in db.execute(consulta).all()
    ]


def total_por_categoria(
    db: Session, usuario_id: int, categoria: str, excluir_id: int | None = None
) -> float:
    consulta = select(func.sum(Gasto.monto)).where(
        Gasto.usuario_id == usuario_id, Gasto.categoria == categoria
    )
    if excluir_id is not None:
        consulta = consulta.where(Gasto.id != excluir_id)
    return db.scalar(consulta) or 0.0


def bloquear_usuario(db: Session, usuario_id: int) -> None:
    """Bloqueo de fila (SELECT ... FOR UPDATE) hasta el commit/rollback: serializa por usuario
    las operaciones que comprueban y luego cambian el total de una categoría."""
    db.scalars(select(Usuario.id).where(Usuario.id == usuario_id).with_for_update()).first()
