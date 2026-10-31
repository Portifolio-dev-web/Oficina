"""Setup único: cria o usuário administrador no Supabase Auth.

Pré-requisitos: supabase_schema.sql e supabase_seed.sql já aplicados no
projeto Supabase, e backend/.env preenchido (SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY, ADMIN_EMAIL, ADMIN_PASSWORD).

Uso:
    python backend/scripts/create_admin.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from supabase_client import get_admin_client  # noqa: E402


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "monitor.informatica25@gmail.com")
    password = os.environ.get("ADMIN_PASSWORD")
    name = os.environ.get("ADMIN_NAME", "Administrador")
    if not password:
        raise SystemExit("Defina ADMIN_PASSWORD em backend/.env antes de rodar este script.")

    db = get_admin_client()
    created = db.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user_id = created.user.id

    # O profile já existe (criado pela trigger on_auth_user_created); só
    # precisamos marcá-lo como admin.
    db.table("profiles").update({"role": "admin", "name": name, "email": email}).eq(
        "id", user_id
    ).execute()

    print(f"Administrador criado: {email} (id={user_id}). profiles.role = 'admin'.")


if __name__ == "__main__":
    main()
