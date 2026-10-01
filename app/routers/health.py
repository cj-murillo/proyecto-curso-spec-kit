from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import salud as salud_repository
from app.services import salud as salud_service

router = APIRouter(tags=["salud"])


def get_salud_repo():
    return salud_repository


@router.get("/health")
def health(
    response: Response,
    db: Session = Depends(get_db),
    repo=Depends(get_salud_repo),
):
    resultado = salud_service.estado(db, repo=repo)
    if resultado["status"] != "ok":
        response.status_code = 503
    return resultado
