# Migración de hashes de contraseña (bcrypt → Argon2)

El proyecto usa `pwdlib` con Argon2. Si una instalación tiene usuarios creados con bcrypt
(p. ej. con `passlib`), hay que migrarlos.

## Por qué no se puede convertir
Un hash es de un solo sentido: sin la contraseña en texto plano no se obtiene su equivalente
en Argon2. Solo hay dos caminos: re-hashear en el momento en que el usuario hace login (única
vez en que se conoce la contraseña) o invalidar el hash y asignar una contraseña nueva.

## Pasos
1. **(Opcional) Conservar logins.** Antes de actualizar, corre una temporada la versión
   anterior (`pwdlib[argon2,bcrypt]` con `verify_and_update` en el login). Cada usuario que
   entre queda con hash Argon2. Mide cuántos faltan:
   `select count(*) from usuarios where hashed_password like '$2%';`
2. **Migrar.** `uv run alembic upgrade head`. La revisión `7c1d2e9a4b30` marca como
   `!bcrypt-invalidado` los hashes `$2a$/$2b$/$2y$` que queden e imprime cuántos fueron.
   En una instalación nueva no toca ninguna fila. El `downgrade` no recupera los hashes.
3. **Recuperar acceso.** Para cada usuario afectado:
   `uv run python -m app.scripts.resetear_password EMAIL` (pide la clave por `getpass`).
