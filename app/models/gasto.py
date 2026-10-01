from datetime import date

from sqlalchemy import Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Gasto(Base):
    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(primary_key=True)
    descripcion: Mapped[str]
    monto: Mapped[float] = mapped_column(Float)
    categoria: Mapped[str]
    fecha: Mapped[date] = mapped_column(default=date.today, server_default=func.current_date())
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
