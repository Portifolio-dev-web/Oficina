"""Setup opcional: recria os 6 agendamentos de demonstração (AF-DEMO01..06)
que antes nasciam de seed_demo() no servidor em memória.

Cria um usuário real por e-mail via Admin API (email_confirm=True, sem
precisar de enviar/verificar código) e, a partir dele, o veículo e o
agendamento correspondentes. Idempotente: se um agendamento com o mesmo id
já existir, ele é pulado.

Uso:
    python backend/scripts/seed_demo.py
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from supabase_client import get_admin_client  # noqa: E402

DEMO = [
    {"id": "AF-DEMO01", "name": "Maria Silva", "email": "maria.silva@demo.oficinafacil.local",
     "vehicle": {"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"},
     "service_ids": ["troca-oleo"], "date_offset": 0, "time": "09:00", "period": "Manhã", "stage": 2},
    {"id": "AF-DEMO02", "name": "João Pereira", "email": "joao.pereira@demo.oficinafacil.local",
     "vehicle": {"make": "Toyota", "model": "Corolla", "plate": "BRA2E19"},
     "service_ids": ["freios"], "date_offset": 0, "time": "10:00", "period": "Manhã", "stage": 1},
    {"id": "AF-DEMO03", "name": "Ana Costa", "email": "ana.costa@demo.oficinafacil.local",
     "vehicle": {"make": "Volkswagen", "model": "T-Cross", "plate": "FZX4A72"},
     "service_ids": ["diag-eletronico"], "date_offset": 0, "time": "08:00", "period": "Manhã", "stage": 3},
    {"id": "AF-DEMO04", "name": "Pedro Santos", "email": "pedro.santos@demo.oficinafacil.local",
     "vehicle": {"make": "Fiat", "model": "Toro", "plate": "GHI3K45"},
     "service_ids": ["revisao-periodica"], "date_offset": 1, "time": "14:00", "period": "Tarde", "stage": 0},
    {"id": "AF-DEMO05", "name": "Lúcia Mendes", "email": "lucia.mendes@demo.oficinafacil.local",
     "vehicle": {"make": "Honda", "model": "HR-V", "plate": "JKL7M88"},
     "service_ids": ["climatizacao"], "date_offset": 0, "time": "11:00", "period": "Manhã", "stage": 4},
    {"id": "AF-DEMO06", "name": "Marcos Rocha", "email": "marcos.rocha@demo.oficinafacil.local",
     "vehicle": {"make": "Hyundai", "model": "Creta", "plate": "MNO9P12"},
     "service_ids": ["alinhamento"], "date_offset": 1, "time": "15:00", "period": "Tarde", "stage": 0},
]


def _get_or_create_customer(db, email: str, name: str) -> str:
    existing = db.table("profiles").select("id").eq("email", email).maybe_single().execute().data
    if existing:
        return existing["id"]
    created = db.auth.admin.create_user(
        {"email": email, "email_confirm": True, "user_metadata": {"name": name}}
    )
    user_id = created.user.id
    db.table("profiles").update({"name": name}).eq("id", user_id).execute()
    return user_id


def _get_or_create_vehicle(db, owner_id: str, vehicle: dict) -> str:
    existing = (
        db.table("vehicles")
        .select("id")
        .eq("owner_id", owner_id)
        .eq("plate", vehicle["plate"])
        .maybe_single()
        .execute()
        .data
    )
    if existing:
        return existing["id"]
    inserted = db.table("vehicles").insert({"owner_id": owner_id, **vehicle}).execute().data
    return inserted[0]["id"]


def main() -> None:
    db = get_admin_client()
    catalog = {s["id"]: s for s in db.table("services").select("id,name,price_cents,duration_minutes").execute().data}

    from datetime import date, timedelta

    today = date.today()

    for item in DEMO:
        if db.table("bookings").select("id").eq("id", item["id"]).maybe_single().execute().data:
            print(f"{item['id']} já existe, pulando.")
            continue

        customer_id = _get_or_create_customer(db, item["email"], item["name"])
        vehicle_id = _get_or_create_vehicle(db, customer_id, item["vehicle"])

        booking = (
            db.table("bookings")
            .insert(
                {
                    "id": item["id"],
                    "customer_id": customer_id,
                    "vehicle_id": vehicle_id,
                    "scheduled_date": (today + timedelta(days=item["date_offset"])).isoformat(),
                    "scheduled_time": item["time"],
                    "period": item["period"],
                    "stage_index": item["stage"],
                }
            )
            .execute()
            .data[0]
        )

        db.table("booking_services").insert(
            [
                {
                    "booking_id": booking["id"],
                    "service_id": sid,
                    "service_name": catalog[sid]["name"],
                    "price_cents": catalog[sid]["price_cents"],
                    "duration_minutes": catalog[sid]["duration_minutes"],
                }
                for sid in item["service_ids"]
            ]
        ).execute()

        print(f"{item['id']} criado (customer={customer_id}).")


if __name__ == "__main__":
    main()
