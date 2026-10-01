"""Reset administrativo de contraseña: uv run python -m app.scripts.resetear_password EMAIL"""
import argparse
import getpass
import sys

from app.database import SessionLocal
from app.services import usuarios as usuarios_service
from app.services.usuarios import UsuarioNoEncontradoError


def main() -> int:
    parser = argparse.ArgumentParser(description="Asigna una contraseña nueva a un usuario.")
    parser.add_argument("email")
    args = parser.parse_args()

    password = getpass.getpass("Nueva contraseña: ")
    if password != getpass.getpass("Repetir contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        usuarios_service.resetear_password(db, args.email, password)
    except UsuarioNoEncontradoError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"Contraseña actualizada para {args.email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
