from datetime import date

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database import Base

HASH = "$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
REV_ANTERIOR = "7c1d2e9a4b30"


def _limpiar(engine):
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("drop table if exists alembic_version"))


def _cfg(pg_engine):
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = pg_engine.url.render_as_string(hide_password=False)
    return cfg


def test_migracion_conserva_gastos_agrega_fecha_y_cascade(pg_engine):
    cfg = _cfg(pg_engine)
    _limpiar(pg_engine)
    try:
        command.upgrade(cfg, REV_ANTERIOR)
        with pg_engine.begin() as conn:
            conn.execute(
                text("insert into usuarios (id, email, hashed_password) values (1, :e, :h)"),
                {"e": "Mayus@Ejemplo.com", "h": HASH},
            )
            conn.execute(
                text(
                    "insert into gastos (descripcion, monto, categoria, usuario_id) "
                    "values ('previo', 10.5, 'comida', 1)"
                )
            )

        command.upgrade(cfg, "head")

        with pg_engine.connect() as conn:
            gasto = conn.execute(text("select descripcion, fecha from gastos")).one()
            email = conn.execute(text("select email from usuarios")).scalar_one()
        assert gasto.descripcion == "previo"
        assert gasto.fecha == date.today()
        assert email == "mayus@ejemplo.com"

        with pg_engine.begin() as conn:
            conn.execute(text("delete from usuarios where id = 1"))
        with pg_engine.connect() as conn:
            assert conn.execute(text("select count(*) from gastos")).scalar_one() == 0
    finally:
        _limpiar(pg_engine)


def test_downgrade_quita_fecha_sin_perder_filas(pg_engine):
    cfg = _cfg(pg_engine)
    _limpiar(pg_engine)
    try:
        command.upgrade(cfg, "head")
        with pg_engine.begin() as conn:
            conn.execute(
                text("insert into usuarios (id, email, hashed_password) values (1, 'a@b.com', :h)"),
                {"h": HASH},
            )
            conn.execute(
                text(
                    "insert into gastos (descripcion, monto, categoria, usuario_id) "
                    "values ('x', 1, 'otros', 1)"
                )
            )

        command.downgrade(cfg, REV_ANTERIOR)

        with pg_engine.connect() as conn:
            columnas = {
                r[0]
                for r in conn.execute(
                    text("select column_name from information_schema.columns where table_name='gastos'")
                )
            }
            assert "fecha" not in columnas
            assert conn.execute(text("select count(*) from gastos")).scalar_one() == 1
    finally:
        _limpiar(pg_engine)
