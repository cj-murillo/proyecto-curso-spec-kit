from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database import Base
from app.security import hash_password

HASH_BCRYPT = "$2b$12$abcdefghijklmnopqrstuuJ5n7r5Q6Vh2b8Ea9Yy3dE0pC1aZ0eqK"


def _limpiar(engine):
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))


def test_migracion_invalida_bcrypt_y_conserva_argon2(pg_engine):
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = pg_engine.url.render_as_string(hide_password=False)
    _limpiar(pg_engine)
    try:
        command.upgrade(cfg, "0ae4f95a815b")
        argon = hash_password("clave123")
        with pg_engine.begin() as conn:
            conn.execute(
                text("insert into usuarios (email, hashed_password) values (:e, :h)"),
                [{"e": "viejo@ejemplo.com", "h": HASH_BCRYPT}, {"e": "nuevo@ejemplo.com", "h": argon}],
            )

        command.upgrade(cfg, "head")

        with pg_engine.connect() as conn:
            filas = dict(conn.execute(text("select email, hashed_password from usuarios")).all())
        assert filas["viejo@ejemplo.com"] == "!bcrypt-invalidado"
        assert filas["nuevo@ejemplo.com"] == argon
    finally:
        _limpiar(pg_engine)
