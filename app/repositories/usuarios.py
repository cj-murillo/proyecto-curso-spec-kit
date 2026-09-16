from sqlalchemy.orm import Session
from app.models.usuario import Usuario


def obtener_por_email(db: Session, email: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.email == email).first()


def guardar(db: Session, email: str, hashed_password: str) -> Usuario:
    usuario = Usuario(email=email, hashed_password=hashed_password)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
