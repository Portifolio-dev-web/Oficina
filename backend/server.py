from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import uuid
import hashlib
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# In-memory mock store (simulates database - no third-party dependencies)
# ---------------------------------------------------------------------------
OTP_STORE = {}        # phone -> code
USERS = {}            # phone -> user dict
APPOINTMENTS = {}     # id -> appointment dict

MOCK_OTP_CODE = "123456"

VEHICLE_MODELS = {
    "Chevrolet": ["Onix", "Onix Plus", "Tracker", "S10", "Spin", "Cruze"],
    "Toyota": ["Corolla", "Corolla Cross", "Hilux", "Yaris", "SW4"],
    "Volkswagen": ["Gol", "Polo", "T-Cross", "Virtus", "Nivus", "Saveiro"],
    "Fiat": ["Argo", "Mobi", "Toro", "Strada", "Pulse"],
    "Honda": ["Civic", "City", "HR-V", "Fit"],
    "Hyundai": ["HB20", "HB20S", "Creta", "Tucson"],
    "Ford": ["Ka", "EcoSport", "Ranger", "Fiesta"],
    "Renault": ["Kwid", "Sandero", "Logan", "Duster"],
    "Nissan": ["Kicks", "Versa", "Frontier"],
    "Jeep": ["Renegade", "Compass", "Commander"],
}

STAGES = [
    "Agendamento Confirmado",
    "Veículo Recebido na Oficina",
    "Diagnóstico / Em Execução",
    "Teste de Rodagem / CQ",
    "Pronto para Retirada",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sms_entry(message):
    return {"id": uuid.uuid4().hex[:10], "message": message, "timestamp": now_iso()}


def vehicle_label(vehicle):
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    plate = vehicle.get("plate", "")
    label = f"{make} {model}".strip()
    return f"{label} ({plate})" if plate else label


def stage_sms(appt, stage):
    nome = appt["user"].get("name", "cliente").split()[0]
    carro = vehicle_label(appt["vehicle"])
    if stage == 0:
        return (f"Olá {nome}, seu agendamento para o {carro} foi confirmado para "
                f"{appt['date']} às {appt['time']}. Link: /rastreio/{appt['id']}")
    if stage == 1:
        return f"{carro} recebido na oficina. Check-in concluído e inspeção inicial registrada."
    if stage == 2:
        return f"Diagnóstico em execução. Nossa equipe está trabalhando no seu {carro}."
    if stage == 3:
        return f"Seu {carro} está em teste de rodagem e controle de qualidade."
    return f"Tudo pronto! Seu {carro} está disponível para retirada. Obrigado pela preferência!"


MECHANICS = [
    {"id": "m1", "name": "Carlos Souza", "specialty": "Motor e transmissão", "available": True},
    {"id": "m2", "name": "Rafael Lima", "specialty": "Freios e suspensão", "available": True},
    {"id": "m3", "name": "Bruno Alves", "specialty": "Elétrica e diagnóstico", "available": False},
    {"id": "m4", "name": "Diego Ferreira", "specialty": "Climatização", "available": True},
    {"id": "m5", "name": "André Santos", "specialty": "Revisão geral", "available": False},
]


def seed_demo():
    if APPOINTMENTS:
        return
    base = datetime.now(timezone.utc).date()

    def d(offset):
        return (base + timedelta(days=offset)).isoformat()

    demo = [
        {"name": "Maria Silva", "phone": "(11) 99999-8888", "vehicle": {"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"},
         "services": [{"id": "troca-oleo", "name": "Troca de óleo e filtros", "price": 189, "duration": "45 min"}], "date": d(0), "time": "09:00", "period": "Manhã", "stage": 2},
        {"name": "João Pereira", "phone": "(11) 98888-7777", "vehicle": {"make": "Toyota", "model": "Corolla", "plate": "BRA2E19"},
         "services": [{"id": "freios", "name": "Sistema de freios", "price": 459, "duration": "1 h 30"}], "date": d(0), "time": "10:00", "period": "Manhã", "stage": 1},
        {"name": "Ana Costa", "phone": "(21) 97777-6666", "vehicle": {"make": "Volkswagen", "model": "T-Cross", "plate": "FZX4A72"},
         "services": [{"id": "diag-eletronico", "name": "Diagnóstico eletrônico", "price": 149, "duration": "40 min"}], "date": d(0), "time": "08:00", "period": "Manhã", "stage": 3},
        {"name": "Pedro Santos", "phone": "(31) 96666-5555", "vehicle": {"make": "Fiat", "model": "Toro", "plate": "GHI3K45"},
         "services": [{"id": "revisao-periodica", "name": "Revisão periódica", "price": 399, "duration": "2 h"}], "date": d(1), "time": "14:00", "period": "Tarde", "stage": 0},
        {"name": "Lúcia Mendes", "phone": "(41) 95555-4444", "vehicle": {"make": "Honda", "model": "HR-V", "plate": "JKL7M88"},
         "services": [{"id": "climatizacao", "name": "Climatização", "price": 349, "duration": "1 h 20"}], "date": d(0), "time": "11:00", "period": "Manhã", "stage": 4},
        {"name": "Marcos Rocha", "phone": "(51) 94444-3333", "vehicle": {"make": "Hyundai", "model": "Creta", "plate": "MNO9P12"},
         "services": [{"id": "alinhamento", "name": "Alinhamento e balanceamento", "price": 159, "duration": "50 min"}], "date": d(1), "time": "15:00", "period": "Tarde", "stage": 0},
    ]
    for i, item in enumerate(demo):
        appt_id = f"AF-DEMO{i + 1:02d}"
        appt = {
            "id": appt_id,
            "user": {"name": item["name"], "phone": item["phone"]},
            "vehicle": item["vehicle"],
            "services": item["services"],
            "date": item["date"],
            "time": item["time"],
            "period": item["period"],
            "statusIndex": item["stage"],
            "status": STAGES[item["stage"]],
            "createdAt": now_iso(),
            "smsLogs": [],
        }
        for st in range(item["stage"] + 1):
            appt["smsLogs"].append(sms_entry(stage_sms(appt, st)))
        APPOINTMENTS[appt_id] = appt


seed_demo()


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"message": "AutoFix Pro Mock API"}


@api_router.post("/auth/send-otp")
async def send_otp(body: SendOtpRequest):
    OTP_STORE[body.phone] = MOCK_OTP_CODE
    logging.info(f"[Simulação SMS] Código OTP para {body.phone}: {MOCK_OTP_CODE}")
    return {
        "success": True,
        "message": "Código SMS enviado com sucesso!",
        "testCode": MOCK_OTP_CODE,
    }


@api_router.post("/auth/verify-otp")
async def verify_otp(body: VerifyOtpRequest):
    expected = OTP_STORE.get(body.phone)
    if not expected or body.code != expected:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    user = USERS.get(body.phone, {})
    user.update({
        "id": user.get("id", uuid.uuid4().hex[:12]),
        "phone": body.phone,
        "name": body.name or user.get("name", ""),
        "vehicle": body.vehicle or user.get("vehicle", {}),
    })
    if body.password:
        user["passwordHash"] = hashlib.sha256(body.password.encode()).hexdigest()
    USERS[body.phone] = user
    OTP_STORE.pop(body.phone, None)

    token = f"mock-jwt-{uuid.uuid4().hex}"
    safe_user = {k: v for k, v in user.items() if k != "passwordHash"}
    return {"success": True, "token": token, "user": safe_user}


@api_router.get("/vehicles/makes")
async def get_makes():
    return {"makes": list(VEHICLE_MODELS.keys())}


@api_router.get("/vehicles/models")
async def get_models(make: str):
    models = VEHICLE_MODELS.get(make)
    if models is None:
        raise HTTPException(status_code=404, detail="Marca não encontrada.")
    return {"make": make, "models": models}


@api_router.post("/appointments")
async def create_appointment(body: AppointmentCreate):
    appt_id = f"AF-{uuid.uuid4().hex[:6].upper()}"
    appt = {
        "id": appt_id,
        "user": body.user,
        "vehicle": body.vehicle,
        "services": body.services,
        "date": body.date,
        "time": body.time,
        "period": body.period,
        "statusIndex": 0,
        "status": STAGES[0],
        "createdAt": now_iso(),
        "smsLogs": [],
    }
    appt["smsLogs"].append(sms_entry(stage_sms(appt, 0)))
    APPOINTMENTS[appt_id] = appt
    logging.info(f"[Simulação SMS] {appt['smsLogs'][0]['message']}")
    return appt


@api_router.get("/tracking/{appointment_id}")
async def get_tracking(appointment_id: str):
    appt = APPOINTMENTS.get(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return appt


@api_router.post("/tracking/{appointment_id}/status")
async def update_status(appointment_id: str, body: Optional[StatusUpdate] = None):
    appt = APPOINTMENTS.get(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")

    if body is not None and body.stage is not None:
        new_stage = body.stage
    else:
        new_stage = appt["statusIndex"] + 1
    new_stage = max(0, min(len(STAGES) - 1, new_stage))

    if new_stage != appt["statusIndex"]:
        appt["statusIndex"] = new_stage
        appt["status"] = STAGES[new_stage]
        appt["smsLogs"].append(sms_entry(stage_sms(appt, new_stage)))
        logging.info(f"[Simulação SMS] {appt['smsLogs'][-1]['message']}")
    return appt


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@2043"
ADMIN_EMAIL = "monitor.informatica25@gmail.com"
ADMIN_TOKENS = set()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


def require_admin(authorization):
    if not authorization or not authorization.startswith("Bearer ") or authorization[7:] not in ADMIN_TOKENS:
        raise HTTPException(status_code=401, detail="Acesso restrito ao administrador.")


@api_router.post("/admin/login")
async def admin_login(body: AdminLoginRequest):
    if body.username not in (ADMIN_USERNAME, ADMIN_EMAIL) or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
    token = f"admin-{uuid.uuid4().hex}"
    ADMIN_TOKENS.add(token)
    return {
        "success": True,
        "token": token,
        "user": {"username": ADMIN_USERNAME, "name": "Administrador", "email": ADMIN_EMAIL},
    }


@api_router.post("/admin/logout")
async def admin_logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        ADMIN_TOKENS.discard(authorization[7:])
    return {"success": True}


@api_router.get("/admin/overview")
async def admin_overview(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    appts = sorted(APPOINTMENTS.values(), key=lambda a: a["createdAt"], reverse=True)
    stats = {
        "total": len(appts),
        "emManutencao": sum(1 for a in appts if 1 <= a["statusIndex"] <= 3),
        "aguardando": sum(1 for a in appts if a["statusIndex"] == 0),
        "prontos": sum(1 for a in appts if a["statusIndex"] == len(STAGES) - 1),
        "mecanicosDisponiveis": sum(1 for m in MECHANICS if m["available"]),
        "mecanicosTotal": len(MECHANICS),
    }
    servicos = {}
    for a in appts:
        for s in a["services"]:
            entry = servicos.setdefault(s["name"], {"name": s["name"], "count": 0, "duration": s.get("duration", "")})
            entry["count"] += 1
    return {
        "stats": stats,
        "appointments": appts,
        "mechanics": MECHANICS,
        "services": list(servicos.values()),
    }


@api_router.post("/admin/mechanics/{mechanic_id}/toggle")
async def toggle_mechanic(mechanic_id: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    for m in MECHANICS:
        if m["id"] == mechanic_id:
            m["available"] = not m["available"]
            return m
    raise HTTPException(status_code=404, detail="Mecânico não encontrado.")


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
