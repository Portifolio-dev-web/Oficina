from fastapi import FastAPI, APIRouter, HTTPException, Header, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import hashlib
import hmac
import logging
import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from settings import get_settings
from supabase_client import get_admin_client, get_auth_client
from rate_limit import check_rate_limit, client_ip
from notifications import send_status_email, send_verification_email

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
# A autenticação de clientes usa e-mail + senha do Supabase Auth: o cadastro
# passa por um código de verificação de 6 dígitos enviado por e-mail via
# SendGrid (/auth/register/send-code, /auth/register/verify-code — código
# guardado com hash em email_verification_tokens, ver supabase_schema.sql); o
# login (/auth/login) é direto com sign_in_with_password, como o do
# administrador (profiles.role = 'admin', ver backend/scripts/create_admin.py).


def _first_or_none(query) -> Optional[dict]:
    """Substitui `.maybe_single()`: nesta versão do postgrest-py (2.33.0),
    `.maybe_single().execute()` devolve `None` diretamente (em vez de um
    objeto com `.data = None`) quando a busca não encontra nenhuma linha —
    quebra com `AttributeError: 'NoneType' object has no attribute 'data'`
    em vez de permitir o 404/401 esperado. `.limit(1)` sempre devolve uma
    lista (vazia ou com um item), nunca `None`."""
    rows = query.limit(1).execute().data
    return rows[0] if rows else None


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
        "user": {"name": profile.get("name", ""), "email": profile.get("email", "")},
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
        "notificationLogs": [
            {"id": h["id"], "message": h["message"], "timestamp": h["created_at"]}
            for h in history
        ],
    }


def _fetch_appointment(booking_id: str) -> Optional[dict]:
    db = get_admin_client()
    booking = _first_or_none(
        db.table("bookings")
        .select("*, vehicles(make,model,plate), profiles(name,email)")
        .eq("id", booking_id)
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


async def _notify_latest_stage(appt: Optional[dict]) -> None:
    """Envia (ou simula, conforme notifications.send_status_email) a mensagem
    da etapa mais recente do agendamento para o e-mail do cliente."""
    if not appt or not appt.get("notificationLogs"):
        return
    email = (appt.get("user") or {}).get("email")
    if not email:
        return
    message = appt["notificationLogs"][-1]["message"]
    await send_status_email(email, message, booking_id=appt["id"])


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


def _get_latest_vehicle(owner_id: str) -> Optional[dict]:
    # frontend/src/pages/Booking.jsx mostra o veículo "ativo" do cliente a
    # partir de session.user.vehicle — devolvemos aqui o mais recente
    # cadastrado por ele (cadastro e login precisam preencher esse campo).
    db = get_admin_client()
    rows = (
        db.table("vehicles")
        .select("make,model,plate")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def _get_profile_by_email(email: str) -> Optional[dict]:
    db = get_admin_client()
    return _first_or_none(
        db.table("profiles").select("id,name,email").eq("email", email)
    )


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(code: str) -> str:
    # SEGURANÇA: só o hash do código vai para o banco (email_verification_tokens)
    # — um dump/leak da tabela não expõe códigos válidos.
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def require_client(authorization: Optional[str]) -> str:
    """Valida o Bearer token e retorna o id do cliente autenticado.

    SEGURANÇA (migração SMS->e-mail): /appointments identificava o cliente
    por um campo "phone" enviado no próprio corpo da requisição, sem
    autenticação nenhuma — qualquer pessoa que soubesse (ou adivinhasse) o
    telefone de outra conta podia agendar em nome dela. Agora exige o mesmo
    Bearer token de sessão já usado por require_admin()/update_status().
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Cliente não autenticado. Faça login antes de agendar."
        )
    token = authorization[7:]

    db = get_admin_client()
    try:
        user = db.auth.get_user(token).user
    except Exception:
        raise HTTPException(
            status_code=401, detail="Cliente não autenticado. Faça login antes de agendar."
        )
    if not user:
        raise HTTPException(
            status_code=401, detail="Cliente não autenticado. Faça login antes de agendar."
        )
    return user.id


# ---------------------------------------------------------------------------
# Request models
#
# SEGURANÇA (auditoria, item S7): nenhum campo de texto tinha max_length nem
# as listas tinham tamanho máximo — um payload grande/abusivo era aceito sem
# limite. Os números abaixo têm folga sobre o que a tela realmente manda (ver
# frontend/src/pages/Booking.jsx, OnboardingModal.jsx), só para rejeitar
# entrada fora do que a aplicação usa, não para apertar o produto.
# ---------------------------------------------------------------------------
class VehicleInput(BaseModel):
    make: str = Field("", max_length=60)
    model: str = Field("", max_length=60)
    plate: Optional[str] = Field(None, max_length=10)


class ServiceSelection(BaseModel):
    id: Optional[str] = Field(None, max_length=64)


class RegisterSendCodeRequest(BaseModel):
    email: EmailStr


class RegisterVerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=120)
    # SEGURANÇA/CORREÇÃO: o Supabase Auth exige mínimo de 6 caracteres por
    # padrão em admin.create_user() — com min_length=4 aqui, o Pydantic
    # aceitava a senha, o código era consumido, e só então a criação do
    # usuário falhava no Supabase ("Password should be at least 6
    # characters."), desperdiçando o código já verificado.
    password: str = Field(..., min_length=6, max_length=128)
    vehicle: Optional[VehicleInput] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class AppointmentCreate(BaseModel):
    vehicle: VehicleInput
    services: List[ServiceSelection] = Field(..., max_length=20)
    date: str = Field(..., max_length=10)
    time: str = Field(..., max_length=8)
    period: Optional[str] = Field("", max_length=20)


class StatusUpdate(BaseModel):
    # Sem max/min de propósito: o clamp em update_status() já trata qualquer
    # valor (inclusive fora da faixa — ver test_status_clamp), então um
    # limite aqui só duplicaria a regra e poderia virar 422 em vez de clamp.
    stage: Optional[int] = None


class AdminLoginRequest(BaseModel):
    username: str = Field(..., max_length=120)
    password: str = Field(..., max_length=128)


class MechanicCreate(BaseModel):
    name: str = Field(..., max_length=120)
    specialty: str = Field("", max_length=120)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"message": "Oficina Fácil API"}


@api_router.post("/auth/register/send-code")
async def register_send_code(body: RegisterSendCodeRequest, request: Request):
    # SEGURANÇA (migração SMS->e-mail, equivalente ao item S4 original):
    # limite por IP (disparo em massa) e por e-mail (não deixa inundar de
    # e-mails uma mesma conta).
    email = body.email.lower()
    check_rate_limit("register-send-code:ip", client_ip(request), limit=5, window_seconds=60)
    check_rate_limit("register-send-code:email", email, limit=5, window_seconds=900)

    if _get_profile_by_email(email):
        raise HTTPException(
            status_code=409, detail="Este e-mail já está cadastrado. Faça login."
        )

    db = get_admin_client()
    code = _generate_code()
    db.table("email_verification_tokens").insert(
        {
            "email": email,
            "code_hash": _hash_code(code),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }
    ).execute()

    sent = await send_verification_email(email, code)
    if not sent:
        raise HTTPException(
            status_code=502, detail="Não foi possível enviar o e-mail. Tente novamente."
        )

    response = {"success": True, "message": "Código enviado para seu e-mail!"}
    if not get_settings().sendgrid_api_key:
        # MODO DEMONSTRAÇÃO: sem SENDGRID_API_KEY, nenhum e-mail de verdade sai
        # (ver notifications.send_verification_email) — devolver o código na
        # resposta é o que permite o fluxo (e os testes de integração)
        # continuarem funcionáveis sem conta num provedor real, igual ao
        # resto do projeto. Nunca ocorre com um provedor de e-mail real
        # configurado.
        response["code"] = code
    return response


@api_router.post("/auth/register/verify-code")
async def register_verify_code(body: RegisterVerifyCodeRequest, request: Request):
    # SEGURANÇA (migração SMS->e-mail, equivalente ao item S4 original): sem
    # isso, o código de 6 dígitos podia ser testado por força bruta sem
    # limite nenhum.
    email = body.email.lower()
    check_rate_limit("register-verify-code:ip", client_ip(request), limit=10, window_seconds=60)
    check_rate_limit("register-verify-code:email", email, limit=10, window_seconds=900)

    db = get_admin_client()
    token_row = (
        db.table("email_verification_tokens")
        .select("id,code_hash,expires_at,consumed_at,attempts")
        .eq("email", email)
        .is_("consumed_at", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    token_row = token_row[0] if token_row else None

    invalid = HTTPException(status_code=400, detail="Código inválido ou expirado.")
    if not token_row or token_row["attempts"] >= 5:
        raise invalid
    if datetime.now(timezone.utc) >= datetime.fromisoformat(token_row["expires_at"]):
        raise invalid
    if not hmac.compare_digest(token_row["code_hash"], _hash_code(body.code)):
        db.table("email_verification_tokens").update(
            {"attempts": token_row["attempts"] + 1}
        ).eq("id", token_row["id"]).execute()
        raise invalid

    db.table("email_verification_tokens").update(
        {"consumed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", token_row["id"]).execute()

    if _get_profile_by_email(email):
        # Corrida rara: duas verificações do mesmo código quase simultâneas.
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado. Faça login.")

    try:
        created = db.auth.admin.create_user(
            {
                "email": email,
                "password": body.password,
                "email_confirm": True,  # já confirmamos nós mesmos, via o código acima
                "user_metadata": {"name": body.name},
            }
        )
    except Exception as exc:
        logger.warning("Falha ao criar usuário após verificação de e-mail: %s", exc)
        # O GoTrue recusa criar um usuário cujo e-mail já existe em auth.users
        # mesmo sem profile correspondente (ex.: e-mail do admin, ou uma conta
        # cujo profile foi apagado manualmente) — nesse caso a mensagem deixa
        # claro o motivo em vez do genérico "não foi possível".
        if "already" in str(exc).lower() or "registered" in str(exc).lower():
            raise HTTPException(
                status_code=409, detail="Este e-mail já está em uso. Faça login."
            )
        raise HTTPException(status_code=400, detail="Não foi possível concluir o cadastro.")

    user_id = created.user.id
    db.table("profiles").update({"name": body.name}).eq("id", user_id).execute()

    if body.vehicle and body.vehicle.make:
        _get_or_create_vehicle(user_id, body.vehicle.model_dump())

    auth = get_auth_client()
    try:
        res = auth.auth.sign_in_with_password({"email": email, "password": body.password})
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Cadastro concluído, mas não foi possível entrar automaticamente. Faça login.",
        )

    profile = db.table("profiles").select("name,email").eq("id", user_id).single().execute().data
    return {
        "success": True,
        "token": res.session.access_token if res.session else None,
        "user": {
            "id": user_id,
            "email": profile["email"],
            "name": profile["name"],
            "vehicle": _get_latest_vehicle(user_id),
        },
    }


@api_router.post("/auth/login")
async def login(body: LoginRequest, request: Request):
    # SEGURANÇA: mesmo limite por IP/conta já aplicado ao login do admin
    # (item S4 da auditoria original) — contra força bruta de senha.
    email = body.email.lower()
    check_rate_limit("login:ip", client_ip(request), limit=10, window_seconds=60)
    check_rate_limit("login:email", email, limit=10, window_seconds=900)

    auth = get_auth_client()
    try:
        res = auth.auth.sign_in_with_password({"email": email, "password": body.password})
    except Exception:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    db = get_admin_client()
    profile = _first_or_none(db.table("profiles").select("name,email").eq("id", res.user.id))
    if not profile:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    return {
        "success": True,
        "token": res.session.access_token if res.session else None,
        "user": {
            "id": res.user.id,
            "email": profile["email"],
            "name": profile["name"],
            "vehicle": _get_latest_vehicle(res.user.id),
        },
    }


@api_router.get("/vehicles/makes")
async def get_makes():
    db = get_admin_client()
    rows = db.table("vehicle_makes").select("name").order("name").execute().data
    return {"makes": [r["name"] for r in rows]}


@api_router.get("/vehicles/models")
async def get_models(make: str):
    db = get_admin_client()
    make_row = _first_or_none(db.table("vehicle_makes").select("id").eq("name", make))
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
async def create_appointment(
    body: AppointmentCreate, authorization: Optional[str] = Header(None)
):
    customer_id = require_client(authorization)
    db = get_admin_client()

    vehicle_id = _get_or_create_vehicle(customer_id, body.vehicle.model_dump())

    service_ids = [s.id for s in body.services if s.id]
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
                "customer_id": customer_id,
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

    appt = _fetch_appointment(booking["id"])
    await _notify_latest_stage(appt)
    return appt


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
    booking = _first_or_none(db.table("bookings").select("stage_index").eq("id", appointment_id))
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    if body is not None and body.stage is not None:
        new_stage = body.stage
    else:
        new_stage = booking["stage_index"] + 1
    new_stage = max(0, min(len(_stage_names()) - 1, new_stage))

    stage_changed = new_stage != booking["stage_index"]
    if stage_changed:
        db.table("bookings").update({"stage_index": new_stage}).eq("id", appointment_id).execute()
        # A entrada correspondente em booking_status_history é criada
        # automaticamente pela trigger bookings_log_stage_change (ver
        # supabase_schema.sql), equivalente ao antigo stage_sms()/notificationLogs.

    appt = _fetch_appointment(appointment_id)
    if stage_changed:
        await _notify_latest_stage(appt)
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

    profile = _first_or_none(db.table("profiles").select("role").eq("id", user.id))
    if not profile or profile.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")
    return user.id


@api_router.post("/admin/login")
async def admin_login(body: AdminLoginRequest, request: Request):
    # SEGURANÇA (auditoria, item S4): limite por IP e por conta contra força
    # bruta de senha — antes não havia nenhum.
    check_rate_limit("admin-login:ip", client_ip(request), limit=10, window_seconds=60)
    check_rate_limit("admin-login:user", body.username.strip().lower(), limit=10, window_seconds=900)

    settings = get_settings()
    email = settings.admin_email if body.username == settings.admin_username else body.username

    auth = get_auth_client()
    try:
        res = auth.auth.sign_in_with_password({"email": email, "password": body.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")

    db = get_admin_client()
    profile = _first_or_none(
        db.table("profiles").select("role,name,email").eq("id", res.user.id)
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
        .select("*, vehicles(make,model,plate), profiles(name,email)")
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


@api_router.post("/admin/mechanics")
async def create_mechanic(body: MechanicCreate, authorization: Optional[str] = Header(None)):
    require_admin(authorization)

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Informe o nome do mecânico.")

    db = get_admin_client()
    created = (
        db.table("mechanics")
        .insert({"name": name, "specialty": body.specialty.strip()})
        .execute()
        .data[0]
    )
    return {
        "id": created["id"],
        "name": created["name"],
        "specialty": created["specialty"],
        "available": created["available"],
    }


@api_router.delete("/admin/mechanics/{mechanic_id}")
async def delete_mechanic(mechanic_id: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)

    try:
        uuid_lib.UUID(mechanic_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Mecânico não encontrado.")

    db = get_admin_client()
    mechanic = _first_or_none(db.table("mechanics").select("id").eq("id", mechanic_id))
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mecânico não encontrado.")

    try:
        db.table("mechanics").delete().eq("id", mechanic_id).execute()
    except Exception as exc:
        # bookings.mechanic_id referencia mechanics(id) sem ON DELETE CASCADE
        # (ver supabase_schema.sql) — remover um mecânico já atribuído a um
        # agendamento vira violação de FK no banco; isso é aceitável (vira um
        # 409 amigável), não um 500.
        logger.warning("Falha ao remover mecânico %s: %s", mechanic_id, exc)
        raise HTTPException(
            status_code=409,
            detail="Não é possível remover: este mecânico está atribuído a algum agendamento.",
        )
    return {"success": True}


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
    mechanic = _first_or_none(db.table("mechanics").select("*").eq("id", mechanic_id))
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # SEGURANÇA (auditoria, item S5): a API não mandava nenhum cabeçalho de
    # segurança. default-src 'none' é seguro aqui porque toda resposta é
    # JSON (a API nunca serve HTML/JS/CSS que precisasse de 'self').
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


# SEGURANÇA (auditoria, item S6): allow_credentials=True com
# CORS_ORIGINS="*" (padrão) é uma combinação inválida/arriscada — e nem é
# necessária aqui. A autenticação é por Bearer token enviado explicitamente
# pelo JS (Authorization), não por cookie, então o navegador nunca precisa
# mandar "credentials" nessas chamadas.
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
