from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import logging
import re
import uuid as uuid_lib
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List

from settings import get_settings
from supabase_client import get_admin_client, get_auth_client

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persistência: Supabase/Postgres (ver supabase_schema.sql e supabase_seed.sql)
# ---------------------------------------------------------------------------
# Este backend não guarda mais nenhum estado em memória — toda leitura e
# escrita (perfis, veículos, catálogo de serviços, mecânicos, agendamentos e
# histórico de rastreamento) passa pelas tabelas criadas em supabase_schema.sql.
# A autenticação de clientes usa o fluxo real de Phone OTP do Supabase Auth
# (sign_in_with_otp / verify_otp) — é necessário configurar um provedor de SMS
# na dashboard do Supabase (Authentication > Providers > Phone) para que o
# código realmente seja enviado. O login de administrador usa email/senha do
# Supabase Auth, com profiles.role = 'admin' (ver backend/scripts/create_admin.py).


@lru_cache
def _stage_names() -> dict:
    db = get_admin_client()
    rows = db.table("tracking_stages").select("stage_index,name").execute().data
    return {row["stage_index"]: row["name"] for row in rows}


def _duration_label(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} h {rest}"
    if hours:
        return f"{hours} h"
    return f"{rest} min"


def _booking_to_dict(booking: dict, services: List[dict], history: List[dict]) -> dict:
    vehicle = booking.get("vehicles") or {}
    profile = booking.get("profiles") or {}
    return {
        "id": booking["id"],
        "user": {"name": profile.get("name", ""), "phone": profile.get("phone", "")},
        "vehicle": {
            "make": vehicle.get("make", ""),
            "model": vehicle.get("model", ""),
            "plate": vehicle.get("plate"),
        },
        "services": [
            {
                "id": s["service_id"],
                "name": s["service_name"],
                "price": s["price_cents"] / 100,
                "duration": _duration_label(s["duration_minutes"]),
            }
            for s in services
        ],
        "date": booking["scheduled_date"],
        "time": str(booking["scheduled_time"])[:5],
        "period": booking.get("period") or "",
        "statusIndex": booking["stage_index"],
        "status": _stage_names().get(booking["stage_index"], ""),
        "createdAt": booking["created_at"],
        "smsLogs": [
            {"id": h["id"], "message": h["message"], "timestamp": h["created_at"]}
            for h in history
        ],
    }


def _fetch_appointment(booking_id: str) -> Optional[dict]:
    db = get_admin_client()
    booking = (
        db.table("bookings")
        .select("*, vehicles(make,model,plate), profiles(name,phone)")
        .eq("id", booking_id)
        .maybe_single()
        .execute()
        .data
    )
    if not booking:
        return None
    services = (
        db.table("booking_services")
        .select("service_id,service_name,price_cents,duration_minutes")
        .eq("booking_id", booking_id)
        .execute()
        .data
    )
    history = (
        db.table("booking_status_history")
        .select("id,message,created_at")
        .eq("booking_id", booking_id)
        .order("created_at")
        .execute()
        .data
    )
    return _booking_to_dict(booking, services, history)


def _get_or_create_vehicle(owner_id: str, vehicle: Optional[dict]) -> str:
    db = get_admin_client()
    vehicle = vehicle or {}
    make = (vehicle.get("make") or "").strip()
    model = (vehicle.get("model") or "").strip()
    plate = (vehicle.get("plate") or "").strip() or None

    query = (
        db.table("vehicles")
        .select("id")
        .eq("owner_id", owner_id)
        .eq("make", make)
        .eq("model", model)
    )
    query = query.eq("plate", plate) if plate else query.is_("plate", "null")
    existing = query.execute().data
    if existing:
        return existing[0]["id"]

    inserted = (
        db.table("vehicles")
        .insert({"owner_id": owner_id, "make": make, "model": model, "plate": plate})
        .execute()
        .data
    )
    return inserted[0]["id"]


def _to_e164(phone: str, default_country_code: str = "55") -> str:
    """Normaliza o telefone mascarado do frontend ("(11) 99999-8888") para o
    formato E.164 exigido pelo Supabase Auth ("+5511999998888"). Assume Brasil
    quando o usuário não digita o código do país."""
    digits = re.sub(r"\D", "", phone)
    if phone.strip().startswith("+"):
        return "+" + digits
    return f"+{default_country_code}{digits}"


def _get_profile_by_phone(phone: str) -> Optional[dict]:
    db = get_admin_client()
    return (
        db.table("profiles")
        .select("id,name,phone")
        .eq("phone", phone)
        .maybe_single()
        .execute()
        .data
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class SendOtpRequest(BaseModel):
    phone: str


class VerifyOtpRequest(BaseModel):
    phone: str
    code: str
    name: Optional[str] = None
    password: Optional[str] = None
    vehicle: Optional[dict] = None


class AppointmentCreate(BaseModel):
    user: dict
    vehicle: dict
    services: List[dict]
    date: str
    time: str
    period: Optional[str] = ""


class StatusUpdate(BaseModel):
    stage: Optional[int] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"message": "Oficina Fácil API"}


@api_router.post("/auth/send-otp")
async def send_otp(body: SendOtpRequest):
    auth = get_auth_client()
    try:
        auth.auth.sign_in_with_otp({"phone": _to_e164(body.phone)})
    except Exception as exc:
        logger.warning("Falha ao enviar OTP para %s: %s", body.phone, exc)
        raise HTTPException(
            status_code=400,
            detail="Não foi possível enviar o código. Verifique o número e tente novamente.",
        )
    return {"success": True, "message": "Código SMS enviado com sucesso!"}


@api_router.post("/auth/verify-otp")
async def verify_otp(body: VerifyOtpRequest):
    auth = get_auth_client()
    try:
        res = auth.auth.verify_otp(
            {"phone": _to_e164(body.phone), "token": body.code, "type": "sms"}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    user = res.user
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    db = get_admin_client()
    if body.name:
        db.table("profiles").update({"name": body.name}).eq("id", user.id).execute()

    if body.vehicle and body.vehicle.get("make"):
        _get_or_create_vehicle(user.id, body.vehicle)

    if body.password:
        try:
            db.auth.admin.update_user_by_id(user.id, {"password": body.password})
        except Exception as exc:
            logger.warning("Não foi possível definir senha para %s: %s", user.id, exc)

    profile = db.table("profiles").select("name,phone").eq("id", user.id).single().execute().data
    return {
        "success": True,
        "token": res.session.access_token if res.session else None,
        "user": {"id": user.id, "phone": profile["phone"], "name": profile["name"]},
    }


@api_router.get("/vehicles/makes")
async def get_makes():
    db = get_admin_client()
    rows = db.table("vehicle_makes").select("name").order("name").execute().data
    return {"makes": [r["name"] for r in rows]}


@api_router.get("/vehicles/models")
async def get_models(make: str):
    db = get_admin_client()
    make_row = (
        db.table("vehicle_makes").select("id").eq("name", make).maybe_single().execute().data
    )
    if not make_row:
        raise HTTPException(status_code=404, detail="Marca não encontrada.")
    rows = (
        db.table("vehicle_models")
        .select("name")
        .eq("make_id", make_row["id"])
        .order("name")
        .execute()
        .data
    )
    return {"make": make, "models": [r["name"] for r in rows]}


@api_router.post("/appointments")
async def create_appointment(body: AppointmentCreate):
    db = get_admin_client()
    phone = body.user.get("phone")
    profile = _get_profile_by_phone(phone) if phone else None
    if not profile:
        raise HTTPException(
            status_code=401, detail="Cliente não autenticado. Faça login antes de agendar."
        )

    vehicle_id = _get_or_create_vehicle(profile["id"], body.vehicle)

    service_ids = [s.get("id") for s in body.services if s.get("id")]
    if not service_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos um serviço.")

    catalog = (
        db.table("services")
        .select("id,name,price_cents,duration_minutes")
        .in_("id", service_ids)
        .eq("active", True)
        .execute()
        .data
    )
    catalog_by_id = {s["id"]: s for s in catalog}
    missing = [sid for sid in service_ids if sid not in catalog_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Serviço(s) inválido(s): {', '.join(missing)}")

    booking = (
        db.table("bookings")
        .insert(
            {
                "customer_id": profile["id"],
                "vehicle_id": vehicle_id,
                "scheduled_date": body.date,
                "scheduled_time": body.time,
                "period": body.period or "",
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
                "service_name": catalog_by_id[sid]["name"],
                "price_cents": catalog_by_id[sid]["price_cents"],
                "duration_minutes": catalog_by_id[sid]["duration_minutes"],
            }
            for sid in service_ids
        ]
    ).execute()

    logger.info("[Simulação SMS] Agendamento %s confirmado para %s", booking["id"], phone)
    return _fetch_appointment(booking["id"])


@api_router.get("/tracking/{appointment_id}")
async def get_tracking(appointment_id: str):
    appt = _fetch_appointment(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return appt


@api_router.post("/tracking/{appointment_id}/status")
async def update_status(
    appointment_id: str,
    body: Optional[StatusUpdate] = None,
    authorization: Optional[str] = Header(None),
):
    # SEGURANÇA (auditoria, item S1): esta rota não exigia autenticação —
    # qualquer pessoa com o ID do agendamento podia avançar/voltar a etapa de
    # QUALQUER cliente. O próprio schema (supabase_schema.sql) já documentava
    # que só o admin deveria alterar a etapa; agora isso é aplicado de fato.
    require_admin(authorization)
    db = get_admin_client()
    booking = (
        db.table("bookings").select("stage_index").eq("id", appointment_id).maybe_single().execute().data
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    if body is not None and body.stage is not None:
        new_stage = body.stage
    else:
        new_stage = booking["stage_index"] + 1
    new_stage = max(0, min(len(_stage_names()) - 1, new_stage))

    if new_stage != booking["stage_index"]:
        db.table("bookings").update({"stage_index": new_stage}).eq("id", appointment_id).execute()
        # A entrada correspondente em booking_status_history é criada
        # automaticamente pela trigger bookings_log_stage_change (ver
        # supabase_schema.sql), equivalente ao antigo stage_sms()/smsLogs.

    appt = _fetch_appointment(appointment_id)
    return appt


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
def require_admin(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")
    token = authorization[7:]

    db = get_admin_client()
    try:
        user = db.auth.get_user(token).user
    except Exception:
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")
    if not user:
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")

    profile = db.table("profiles").select("role").eq("id", user.id).maybe_single().execute().data
    if not profile or profile.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")
    return user.id


@api_router.post("/admin/login")
async def admin_login(body: AdminLoginRequest):
    settings = get_settings()
    email = settings.admin_email if body.username == settings.admin_username else body.username

    auth = get_auth_client()
    try:
        res = auth.auth.sign_in_with_password({"email": email, "password": body.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

    db = get_admin_client()
    profile = (
        db.table("profiles").select("role,name,email").eq("id", res.user.id).maybe_single().execute().data
    )
    if not profile or profile.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

    return {
        "success": True,
        "token": res.session.access_token,
        "user": {
            "username": settings.admin_username,
            "name": profile.get("name") or "Administrador",
            "email": profile.get("email") or email,
        },
    }


@api_router.post("/admin/logout")
async def admin_logout(authorization: Optional[str] = Header(None)):
    # Melhor esforço: revoga a sessão associada a este token no GoTrue. Como
    # o access token é um JWT stateless, ele continua válido (assinatura
    # intacta) até expirar naturalmente — revogar a sessão impede a emissão
    # de NOVOS tokens via refresh, mas não garante invalidação imediata do
    # token atual em todo provedor. Para expiração mais curta, ajuste "JWT
    # expiry limit" em Supabase Dashboard > Authentication > Sessions.
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            get_admin_client().auth.admin.sign_out(token, "global")
        except Exception as exc:
            logger.warning("Falha ao invalidar sessão admin: %s", exc)
    return {"success": True}


@api_router.get("/admin/overview")
async def admin_overview(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    db = get_admin_client()

    bookings = (
        db.table("bookings")
        .select("*, vehicles(make,model,plate), profiles(name,phone)")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    appts = []
    for booking in bookings:
        services = (
            db.table("booking_services")
            .select("service_id,service_name,price_cents,duration_minutes")
            .eq("booking_id", booking["id"])
            .execute()
            .data
        )
        history = (
            db.table("booking_status_history")
            .select("id,message,created_at")
            .eq("booking_id", booking["id"])
            .order("created_at")
            .execute()
            .data
        )
        appts.append(_booking_to_dict(booking, services, history))

    mechanics = db.table("mechanics").select("id,name,specialty,available").order("name").execute().data

    last_stage = len(_stage_names()) - 1
    stats = {
        "total": len(appts),
        "emManutencao": sum(1 for a in appts if 1 <= a["statusIndex"] <= last_stage - 1),
        "aguardando": sum(1 for a in appts if a["statusIndex"] == 0),
        "prontos": sum(1 for a in appts if a["statusIndex"] == last_stage),
        "mecanicosDisponiveis": sum(1 for m in mechanics if m["available"]),
        "mecanicosTotal": len(mechanics),
    }

    servicos = {}
    for appt in appts:
        for s in appt["services"]:
            entry = servicos.setdefault(s["name"], {"name": s["name"], "count": 0, "duration": s["duration"]})
            entry["count"] += 1

    return {
        "stats": stats,
        "appointments": appts,
        "mechanics": mechanics,
        "services": list(servicos.values()),
    }


@api_router.post("/admin/mechanics/{mechanic_id}/toggle")
async def toggle_mechanic(mechanic_id: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)

    # mechanics.id é UUID no Postgres; um id malformado faria a query abaixo
    # falhar com erro de sintaxe no banco em vez de simplesmente não achar
    # nada, então validamos o formato antes de consultar.
    try:
        uuid_lib.UUID(mechanic_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Mecânico não encontrado.")

    db = get_admin_client()
    mechanic = db.table("mechanics").select("*").eq("id", mechanic_id).maybe_single().execute().data
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mecânico não encontrado.")

    updated = (
        db.table("mechanics")
        .update({"available": not mechanic["available"]})
        .eq("id", mechanic_id)
        .execute()
        .data[0]
    )
    return {
        "id": updated["id"],
        "name": updated["name"],
        "specialty": updated["specialty"],
        "available": updated["available"],
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
