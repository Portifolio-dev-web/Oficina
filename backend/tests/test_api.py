"""Testes de integração do backend contra um projeto Supabase real.

Desde a migração para Supabase (ver supabase_schema.sql), este backend não
tem mais estado em memória, então estes testes exigem um backend rodando de
verdade (API_BASE_URL) ligado a um projeto Supabase com o schema e o seed de
catálogo aplicados (supabase_schema.sql + supabase_seed.sql).

Para os testes de OTP sem depender de SMS real, cadastre um número em
Supabase Dashboard > Authentication > Test phone numbers com um código fixo,
e exporte TEST_OTP_PHONE / TEST_OTP_CODE (ver backend/.env.example).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

TEST_OTP_PHONE = os.environ.get("TEST_OTP_PHONE")
TEST_OTP_CODE = os.environ.get("TEST_OTP_CODE")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="Requer um projeto Supabase configurado (ver backend/.env.example).",
)

requires_test_otp = pytest.mark.skipif(
    not (TEST_OTP_PHONE and TEST_OTP_CODE),
    reason="Defina TEST_OTP_PHONE/TEST_OTP_CODE (Supabase Test phone numbers) para testar OTP.",
)

# SEGURANÇA (auditoria, item S1): POST /tracking/{id}/status agora exige um
# admin autenticado, então os testes de troca de etapa também precisam de
# ADMIN_PASSWORD (mesma credencial usada em test_admin_api.py).
requires_admin = pytest.mark.skipif(
    not ADMIN_PASSWORD,
    reason="Defina ADMIN_PASSWORD (ver backend/.env.example) para testar troca de status.",
)


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


# --- Auth / OTP ---
@requires_test_otp
class TestAuth:
    def test_send_otp(self, session):
        r = session.post(f"{API}/auth/send-otp", json={"phone": TEST_OTP_PHONE})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_verify_otp_wrong(self, session):
        session.post(f"{API}/auth/send-otp", json={"phone": TEST_OTP_PHONE})
        r = session.post(
            f"{API}/auth/verify-otp", json={"phone": TEST_OTP_PHONE, "code": "000000"}
        )
        assert r.status_code == 400

    def test_verify_otp_ok(self, session):
        session.post(f"{API}/auth/send-otp", json={"phone": TEST_OTP_PHONE})
        r = session.post(
            f"{API}/auth/verify-otp",
            json={
                "phone": TEST_OTP_PHONE,
                "code": TEST_OTP_CODE,
                "name": "Teste Silva",
                "password": "senha-teste-1234",
                "vehicle": {"make": "Chevrolet", "model": "Onix"},
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert isinstance(d["token"], str) and len(d["token"]) > 10
        assert d["user"]["name"] == "Teste Silva"
        assert "passwordHash" not in d["user"]


# --- Vehicles (catálogo público, não depende de OTP) ---
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
@requires_test_otp
class TestAppointmentsTracking:
    @pytest.fixture(scope="class")
    def appt_id(self, session):
        # Garante que exista um profile para TEST_OTP_PHONE antes de agendar
        # (criar o agendamento exige um cliente autenticado via OTP).
        session.post(f"{API}/auth/send-otp", json={"phone": TEST_OTP_PHONE})
        session.post(
            f"{API}/auth/verify-otp",
            json={"phone": TEST_OTP_PHONE, "code": TEST_OTP_CODE, "name": "Teste Silva"},
        )

        payload = {
            "user": {"name": "Teste Silva", "phone": TEST_OTP_PHONE},
            "vehicle": {"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"},
            "services": [{"id": "troca-oleo"}],
            "date": "2026-02-15",
            "time": "09:00",
            "period": "Manhã",
        }
        r = session.post(f"{API}/appointments", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"].startswith("AF-")
        assert d["status"] == "Agendamento Confirmado"
        assert d["statusIndex"] == 0
        assert len(d["smsLogs"]) == 1
        return d["id"]

    def test_tracking_get(self, session, appt_id):
        r = session.get(f"{API}/tracking/{appt_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == appt_id
        assert d["vehicle"]["make"] == "Chevrolet"
        assert len(d["services"]) == 1
        assert len(d["smsLogs"]) >= 1

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
        assert len(d["smsLogs"]) == 2

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
