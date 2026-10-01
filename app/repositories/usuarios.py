from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.usuario import Usuario


def obtener_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalars(select(Usuario).where(Usuario.email == email)).first()


def guardar(db: Session, email: str, hashed_password: str) -> Usuario:
    usuario = Usuario(email=email, hashed_password=hashed_password)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_password(db: Session, usuario: Usuario, hashed_password: str) -> Usuario:
    usuario.hashed_password = hashed_password
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_email(db: Session, usuario: Usuario, email: str) -> Usuario | None:
    """None si el email ya existe (índice único), incluso ante una carrera."""
    usuario.email = email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(usuario)
    return usuario


def eliminar(db: Session, usuario: Usuario) -> None:
    """Borra el usuario; la base elimina sus gastos (ON DELETE CASCADE)."""
    db.delete(usuario)
    db.commit()
