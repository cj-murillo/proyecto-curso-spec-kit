FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Copiar el binario de uv desde su propia imagen oficial (recomendado por Astral).
# Pineado a una versión específica, no ":latest" — ver el porqué en practica_10.md.
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /usr/local/bin/

# 1) Copiar SOLO los archivos de dependencias primero: así esta capa
#    se reutiliza en cache mientras no cambien pyproject.toml / uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Ahora sí copiar el código de la aplicación
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Instala el propio paquete del proyecto (si tu pyproject define uno)
RUN uv sync --frozen --no-dev

# Buena práctica de seguridad (Artículo IV): no correr como root
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Esta imagen sirve para dos roles (backend y migraciones); docker-compose.yml
# decide cuál con "command:". Este CMD es el rol por defecto (backend).
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
