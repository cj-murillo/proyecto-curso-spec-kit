from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def base_disponible(db: Session) -> bool:
    try:
        db.execute(select(1))
        return True
    except SQLAlchemyError:
        return False
