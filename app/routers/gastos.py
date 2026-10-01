from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.gasto import (
    CategoriasResponse,
    FiltrosGastos,
    FiltrosResumen,
    GastoCreate,
    GastoPatch,
    GastoResponse,
    GastoUpdate,
    ResumenGastos,
)
from app.services import gastos as gastos_service
from app.services.gastos import (
    AccesoDenegadoError,
    CategoriaInvalidaError,
    GastoNoEncontradoError,
    LimiteExcedidoError,
)
from app.dependencies import get_current_user, get_gastos_repo
from app.models.usuario import Usuario

router = APIRouter(prefix="/gastos", tags=["gastos"])


@router.post("/", response_model=GastoResponse, status_code=201)
def crear(
    datos: GastoCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    try:
        extra = {} if datos.fecha is None else {"fecha": datos.fecha}
        return gastos_service.registrar_gasto(
            db, usuario_actual.id, datos.descripcion, datos.monto, datos.categoria, repo=repo, **extra
        )
    except (ValueError, CategoriaInvalidaError, LimiteExcedidoError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[GastoResponse])
def listar(
    response: Response,
    filtros: Annotated[FiltrosGastos, Query()],
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    criterios = filtros.model_dump(exclude={"skip", "limit"}, exclude_none=True)
    try:
        gastos = gastos_service.listar_gastos(
            db, usuario_actual.id, filtros.skip, filtros.limit, repo=repo, **criterios
        )
        total = gastos_service.contar_gastos(
            db, usuario_actual.id, repo=repo, **{k: v for k, v in criterios.items() if k != "orden"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if total is not None:
        response.headers["X-Total-Count"] = str(total)
    return gastos


@router.get("/resumen", response_model=ResumenGastos)
def resumen(
    filtros: Annotated[FiltrosResumen, Query()],
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    return gastos_service.resumen_gastos(
        db, usuario_actual.id, filtros.desde, filtros.hasta, repo=repo
    )


@router.get("/categorias", response_model=CategoriasResponse)
def categorias(usuario_actual: Usuario = Depends(get_current_user)):
    return gastos_service.info_categorias()


def _traducir(exc: Exception) -> HTTPException:
    if isinstance(exc, GastoNoEncontradoError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, AccesoDenegadoError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


ERRORES_GASTO = (
    ValueError,
    CategoriaInvalidaError,
    LimiteExcedidoError,
    GastoNoEncontradoError,
    AccesoDenegadoError,
)


@router.get("/{gasto_id}", response_model=GastoResponse)
def obtener(
    gasto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    try:
        return gastos_service.obtener_gasto(db, usuario_actual.id, gasto_id, repo=repo)
    except ERRORES_GASTO as e:
        raise _traducir(e)


@router.put("/{gasto_id}", response_model=GastoResponse)
def reemplazar(
    gasto_id: int,
    datos: GastoUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    try:
        return gastos_service.actualizar_gasto(
            db, usuario_actual.id, gasto_id, datos.model_dump(), repo=repo
        )
    except ERRORES_GASTO as e:
        raise _traducir(e)


@router.patch("/{gasto_id}", response_model=GastoResponse)
def modificar(
    gasto_id: int,
    datos: GastoPatch,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    try:
        return gastos_service.actualizar_gasto(
            db, usuario_actual.id, gasto_id, datos.model_dump(exclude_unset=True), repo=repo
        )
    except ERRORES_GASTO as e:
        raise _traducir(e)


@router.delete("/{gasto_id}", status_code=204)
def eliminar(
    gasto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    try:
        gastos_service.eliminar_gasto(db, usuario_actual.id, gasto_id, repo=repo)
    except ERRORES_GASTO as e:
        raise _traducir(e)
    return Response(status_code=204)
