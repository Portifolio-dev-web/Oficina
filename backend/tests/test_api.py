"""Backend API tests for AutoFix Pro mock endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://shop-scheduling-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Auth / OTP ---
class TestAuth:
    def test_send_otp(self, session):
        r = session.post(f"{API}/auth/send-otp", json={"phone": "11999998888"})
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["testCode"] == "123456"

    def test_verify_otp_wrong(self, session):
        session.post(f"{API}/auth/send-otp", json={"phone": "11999998888"})
        r = session.post(f"{API}/auth/verify-otp", json={"phone": "11999998888", "code": "000000"})
        assert r.status_code == 400

    def test_verify_otp_ok(self, session):
        session.post(f"{API}/auth/send-otp", json={"phone": "11999998888"})
        r = session.post(f"{API}/auth/verify-otp", json={
            "phone": "11999998888", "code": "123456",
            "name": "Teste Silva", "password": "1234",
            "vehicle": {"make": "Chevrolet", "model": "Onix"}
        })
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["token"].startswith("mock-jwt-")
        assert d["user"]["name"] == "Teste Silva"
        assert "passwordHash" not in d["user"]


# --- Vehicles ---
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
    def appt_id(self, session):
        payload = {
            "user": {"name": "Teste Silva", "phone": "11999998888"},
            "vehicle": {"make": "Chevrolet", "model": "Onix", "plate": "ABC1D23"},
            "services": [{"id": "s1", "name": "Troca de Óleo", "price": 150}],
            "date": "2026-02-15",
            "time": "09:00",
            "period": "manha",
        }
        r = session.post(f"{API}/appointments", json=payload)
        assert r.status_code == 200
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

    def test_status_advance_default(self, session, appt_id):
        r = session.post(f"{API}/tracking/{appt_id}/status", json={})
        assert r.status_code == 200
        d = r.json()
        assert d["statusIndex"] == 1
        assert d["status"] == "Veículo Recebido na Oficina"
        assert len(d["smsLogs"]) == 2

    def test_status_jump(self, session, appt_id):
        r = session.post(f"{API}/tracking/{appt_id}/status", json={"stage": 4})
        assert r.status_code == 200
        d = r.json()
        assert d["statusIndex"] == 4
        assert d["status"] == "Pronto para Retirada"

    def test_status_clamp(self, session, appt_id):
        r = session.post(f"{API}/tracking/{appt_id}/status", json={"stage": 99})
        assert r.status_code == 200
        assert r.json()["statusIndex"] == 4

        r = session.post(f"{API}/tracking/{appt_id}/status", json={"stage": 0})
        assert r.status_code == 200
        assert r.json()["statusIndex"] == 0
