from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.gasto import GastoCreate, GastoResponse
from app.services import gastos as gastos_service
from app.services.gastos import CategoriaInvalidaError, LimiteExcedidoError
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
        return gastos_service.registrar_gasto(
            db, usuario_actual.id, datos.descripcion, datos.monto, datos.categoria, repo=repo
        )
    except (ValueError, CategoriaInvalidaError, LimiteExcedidoError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[GastoResponse])
def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
    repo=Depends(get_gastos_repo),
):
    return gastos_service.listar_gastos(db, usuario_actual.id, skip, limit, repo=repo)
