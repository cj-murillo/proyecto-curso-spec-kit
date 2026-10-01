from app.repositories import salud as salud_repository


def estado(db, repo=salud_repository) -> dict:
    if repo.base_disponible(db):
        return {"status": "ok", "db": "ok"}
    return {"status": "degraded", "db": "error"}
