"""gastos: fecha, FK con ON DELETE CASCADE, indice por usuario y emails en minusculas

Revision ID: a3f5c8d1e2b4
Revises: 7c1d2e9a4b30
Create Date: 2026-10-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f5c8d1e2b4'
down_revision: Union[str, Sequence[str], None] = '7c1d2e9a4b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _nombre_fk_usuario() -> str | None:
    for fk in sa.inspect(op.get_bind()).get_foreign_keys("gastos"):
        if fk["referred_table"] == "usuarios" and fk["constrained_columns"] == ["usuario_id"]:
            return fk["name"]
    return None


def upgrade() -> None:
    # Postgres rellena las filas existentes con la fecha de la migracion en el mismo ALTER.
    op.add_column(
        "gastos",
        sa.Column("fecha", sa.Date(), nullable=False, server_default=sa.func.current_date()),
    )

    nombre = _nombre_fk_usuario()
    if nombre:
        op.drop_constraint(nombre, "gastos", type_="foreignkey")
    op.create_foreign_key(
        "fk_gastos_usuario_id", "gastos", "usuarios", ["usuario_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_gastos_usuario_id", "gastos", ["usuario_id"])

    usuarios = sa.table("usuarios", sa.column("email", sa.String))
    op.get_bind().execute(usuarios.update().values(email=sa.func.lower(usuarios.c.email)))


def downgrade() -> None:
    """Revierte esquema. La normalizacion de emails a minusculas NO se revierte."""
    op.drop_index("ix_gastos_usuario_id", table_name="gastos")
    op.drop_constraint("fk_gastos_usuario_id", "gastos", type_="foreignkey")
    op.create_foreign_key("gastos_usuario_id_fkey", "gastos", "usuarios", ["usuario_id"], ["id"])
    op.drop_column("gastos", "fecha")
