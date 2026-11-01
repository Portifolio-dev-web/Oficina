"""Testes de integração do backend contra um projeto Supabase real.

Desde a migração para Supabase (ver supabase_schema.sql), este backend não
tem mais estado em memória, então estes testes exigem um backend rodando de
verdade (API_BASE_URL) ligado a um projeto Supabase com o schema e o seed de
catálogo aplicados (supabase_schema.sql + supabase_seed.sql).

Os testes de cadastro/login não dependem de nenhuma conta num provedor de
e-mail real: sem RESEND_API_KEY configurada, POST /auth/register/send-code
devolve o próprio código na resposta (modo demonstração, ver
backend/server.py e backend/.env.example), e é isso que os testes usam. Cada
teste usa um e-mail aleatório (uuid4) para não colidir com execuções
anteriores, já que profiles.email agora é único.
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="Requer um projeto Supabase configurado (ver backend/.env.example).",
)

# SEGURANÇA (auditoria, item S1): POST /tracking/{id}/status agora exige um
# admin autenticado, então os testes de troca de etapa também precisam de
# ADMIN_PASSWORD (mesma credencial usada em test_admin_api.py).
requires_admin = pytest.mark.skipif(
    not ADMIN_PASSWORD,
    reason="Defina ADMIN_PASSWORD (ver backend/.env.example) para testar troca de status.",
)


def _random_email() -> str:
    return f"teste-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_auth_header(session):
    r = session.post(
        f"{API}/admin/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _register(session, email, *, name="Teste Silva", password="senha-teste-1234", vehicle=None):
    r = session.post(f"{API}/auth/register/send-code", json={"email": email})
    assert r.status_code == 200, r.text
    code = r.json().get("code")
    assert code, "RESEND_API_KEY está configurada: sem o modo demonstração, não há como ler o código nos testes."

    payload = {"email": email, "code": code, "name": name, "password": password}
    if vehicle is not None:
        payload["vehicle"] = vehicle
    r = session.post(f"{API}/auth/register/verify-code", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# --- Auth / Cadastro e login por e-mail ---
class TestAuth:
    def test_register_send_code(self, session):
        r = session.post(f"{API}/auth/register/send-code", json={"email": _random_email()})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_register_verify_code_wrong(self, session):
        email = _random_email()
        session.post(f"{API}/auth/register/send-code", json={"email": email})
        r = session.post(
            f"{API}/auth/register/verify-code",
            json={"email": email, "code": "000000", "name": "Teste", "password": "senha-teste-1234"},
        )
        assert r.status_code == 400

    def test_register_verify_code_ok(self, session):
        d = _register(session, _random_email(), vehicle={"make": "Chevrolet", "model": "Onix"})
        assert d["success"] is True
        assert isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["user"]["name"] == "Teste Silva"
        assert "passwordHash" not in d["user"]

    def test_register_duplicate_email_rejected(self, session):
        email = _random_email()
        _register(session, email)
        r = session.post(f"{API}/auth/register/send-code", json={"email": email})
        assert r.status_code == 409

    def test_login_wrong_password(self, session):
        email = _random_email()
        _register(session, email, password="senha-teste-1234")
        r = session.post(f"{API}/auth/login", json={"email": email, "password": "errada"})
        assert r.status_code == 401

    def test_login_ok(self, session):
        email = _random_email()
        _register(session, email, password="senha-teste-1234")
        r = session.post(f"{API}/auth/login", json={"email": email, "password": "senha-teste-1234"})
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["user"]["email"] == email


# --- Vehicles (catálogo público, não depende de autenticação) ---
class TestVehicles:
    def test_models_chevrolet(self, session):
        r = session.get(f"{API}/vehicles/models", params={"make": "Chevrolet"})
        assert r.status_code == 200
        d = r.json()
        assert "Onix" in d["models"]
        assert "Tracker" in d["models"]
        assert "S10" in d["models"]

    def test_models_unknown(self, session):
        r = session.get(f"{API}/vehicles/models", params={"make": "NoBrand"})
        assert r.status_code == 404


# --- Appointments + Tracking ---
class TestAppointmentsTracking:
    @pytest.fixture(scope="class")
    def client_auth_header(self, session):
        d = _register(session, _random_email(), vehicle={"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"})
        return {"Authorization": f"Bearer {d['token']}"}

    @pytest.fixture(scope="class")
    def appt_id(self, session, client_auth_header):
        payload = {
            "vehicle": {"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"},
            "services": [{"id": "troca-oleo"}],
            "date": "2026-02-15",
            "time": "09:00",
            "period": "Manhã",
        }
        r = session.post(f"{API}/appointments", json=payload, headers=client_auth_header)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"].startswith("AF-")
        assert d["status"] == "Agendamento Confirmado"
        assert d["statusIndex"] == 0
        assert len(d["notificationLogs"]) == 1
        return d["id"]

    def test_appointments_requires_auth(self, session):
        payload = {
            "vehicle": {"make": "Chevrolet", "model": "Onix"},
            "services": [{"id": "troca-oleo"}],
            "date": "2026-02-15",
            "time": "09:00",
            "period": "Manhã",
        }
        r = session.post(f"{API}/appointments", json=payload)
        assert r.status_code == 401

    def test_tracking_get(self, session, appt_id):
        r = session.get(f"{API}/tracking/{appt_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == appt_id
        assert d["vehicle"]["make"] == "Chevrolet"
        assert len(d["services"]) == 1
        assert len(d["notificationLogs"]) >= 1

    def test_tracking_not_found(self, session):
        r = session.get(f"{API}/tracking/AF-XXXXXX")
        assert r.status_code == 404

    def test_status_requires_admin(self, session, appt_id):
        r = session.post(f"{API}/tracking/{appt_id}/status", json={})
        assert r.status_code == 401

    @requires_admin
    def test_status_advance_default(self, session, appt_id, admin_auth_header):
        r = session.post(f"{API}/tracking/{appt_id}/status", json={}, headers=admin_auth_header)
        assert r.status_code == 200
        d = r.json()
        assert d["statusIndex"] == 1
        assert d["status"] == "Veículo Recebido na Oficina"
        assert len(d["notificationLogs"]) == 2

    @requires_admin
    def test_status_jump(self, session, appt_id, admin_auth_header):
        r = session.post(
            f"{API}/tracking/{appt_id}/status", json={"stage": 4}, headers=admin_auth_header
        )
        assert r.status_code == 200
        d = r.json()
        assert d["statusIndex"] == 4
        assert d["status"] == "Pronto para Retirada"

    @requires_admin
    def test_status_clamp(self, session, appt_id, admin_auth_header):
        r = session.post(
            f"{API}/tracking/{appt_id}/status", json={"stage": 99}, headers=admin_auth_header
        )
        assert r.status_code == 200
        assert r.json()["statusIndex"] == 4

        r = session.post(
            f"{API}/tracking/{appt_id}/status", json={"stage": 0}, headers=admin_auth_header
        )
        assert r.status_code == 200
        assert r.json()["statusIndex"] == 0
