"""invalidar hashes bcrypt

Revision ID: 7c1d2e9a4b30
Revises: 0ae4f95a815b
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c1d2e9a4b30'
down_revision: Union[str, Sequence[str], None] = '0ae4f95a815b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HASH_INVALIDADO = "!bcrypt-invalidado"


def upgrade() -> None:
    """Invalida los hashes bcrypt: sin la contraseña en claro no se pueden convertir a Argon2.

    Los usuarios afectados recuperan el acceso con
    `uv run python -m app.scripts.resetear_password EMAIL`.
    """
    usuarios = sa.table("usuarios", sa.column("hashed_password", sa.String))
    col = usuarios.c.hashed_password
    resultado = op.get_bind().execute(
        usuarios.update()
        .where(sa.or_(col.startswith("$2a$"), col.startswith("$2b$"), col.startswith("$2y$")))
        .values(hashed_password=HASH_INVALIDADO)
    )
    print(f"Hashes bcrypt invalidados: {resultado.rowcount} usuario(s) requieren reset de contraseña.")


def downgrade() -> None:
    """No-op: el hash bcrypt original no se puede recuperar."""
