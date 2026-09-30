"""Admin dashboard API tests for Oficina Fácil - password-protected admin panel."""
import os
import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_USER = "admin"
ADMIN_EMAIL = "monitor.informatica25@gmail.com"
ADMIN_PASS = "admin@2043"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(client):
    r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# --- POST /api/admin/login ---
class TestAdminLogin:
    def test_login_wrong_password(self, client):
        r = client.post(f"{API}/admin/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401
        assert "inválid" in r.json()["detail"].lower()

    def test_login_wrong_user(self, client):
        r = client.post(f"{API}/admin/login", json={"username": "nobody", "password": ADMIN_PASS})
        assert r.status_code == 401

    def test_login_success_admin(self, client):
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["token"], str) and len(data["token"]) > 10
        assert data["user"]["username"] == "admin"

    def test_login_success_email_as_username(self, client):
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200
        assert isinstance(r.json()["token"], str)


# --- GET /api/admin/overview (auth required) ---
class TestAdminOverviewAuth:
    def test_overview_no_token(self, client):
        r = client.get(f"{API}/admin/overview")
        assert r.status_code == 401

    def test_overview_bad_token(self, client):
        r = client.get(f"{API}/admin/overview", headers=auth("bogus"))
        assert r.status_code == 401

    def test_overview_with_token(self, client, token):
        r = client.get(f"{API}/admin/overview", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        for k in ("stats", "appointments", "mechanics", "services"):
            assert k in data
        assert data["stats"]["total"] >= 6
        assert data["stats"]["mecanicosTotal"] == 5
        ids = [a["id"] for a in data["appointments"]]
        for i in range(1, 7):
            assert f"AF-DEMO{i:02d}" in ids


# --- POST /api/admin/mechanics/{id}/toggle (auth required) ---
class TestMechanicToggleAuth:
    def test_toggle_no_token(self, client):
        r = client.post(f"{API}/admin/mechanics/m2/toggle")
        assert r.status_code == 401

    def test_toggle_with_token(self, client, token):
        before = next(m for m in client.get(f"{API}/admin/overview", headers=auth(token)).json()["mechanics"] if m["id"] == "m2")["available"]
        r = client.post(f"{API}/admin/mechanics/m2/toggle", headers=auth(token))
        assert r.status_code == 200
        assert r.json()["available"] == (not before)
        # restore
        client.post(f"{API}/admin/mechanics/m2/toggle", headers=auth(token))

    def test_toggle_invalid_id(self, client, token):
        r = client.post(f"{API}/admin/mechanics/does-not-exist/toggle", headers=auth(token))
        assert r.status_code == 404


# --- POST /api/admin/logout invalidates token ---
class TestAdminLogout:
    def test_logout_invalidates_token(self, client):
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        tok = r.json()["token"]
        # token works
        assert client.get(f"{API}/admin/overview", headers=auth(tok)).status_code == 200
        # logout
        r2 = client.post(f"{API}/admin/logout", headers=auth(tok))
        assert r2.status_code == 200
        # token no longer works
        assert client.get(f"{API}/admin/overview", headers=auth(tok)).status_code == 401


# --- Regression: public customer flows remain unprotected ---
class TestPublicRegression:
    def test_send_otp_public(self, client):
        r = client.post(f"{API}/auth/send-otp", json={"phone": "(11) 99999-0000"})
        assert r.status_code == 200
        assert r.json()["testCode"] == "123456"

    def test_verify_otp_public(self, client):
        client.post(f"{API}/auth/send-otp", json={"phone": "(11) 99999-1234"})
        r = client.post(f"{API}/auth/verify-otp", json={
            "phone": "(11) 99999-1234", "code": "123456", "name": "TEST_User",
            "password": "abcd", "vehicle": {"make": "Fiat", "model": "Mobi", "plate": "TST0A00"}
        })
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_tracking_get_public(self, client):
        r = client.get(f"{API}/tracking/AF-DEMO01")
        assert r.status_code == 200

    def test_tracking_status_public(self, client):
        # Advance & regress without auth
        appt = client.get(f"{API}/tracking/AF-DEMO01").json()
        original = appt["statusIndex"]
        target = min(4, original + 1) if original < 4 else max(0, original - 1)
        r = client.post(f"{API}/tracking/AF-DEMO01/status", json={"stage": target})
        assert r.status_code == 200
        assert r.json()["statusIndex"] == target
        # restore
        client.post(f"{API}/tracking/AF-DEMO01/status", json={"stage": original})

    def test_create_appointment_public(self, client):
        r = client.post(f"{API}/appointments", json={
            "user": {"name": "TEST_Reg", "phone": "(11) 90000-0000"},
            "vehicle": {"make": "Toyota", "model": "Yaris", "plate": "TST1B11"},
            "services": [{"id": "troca-oleo", "name": "Troca de óleo", "price": 189, "duration": "45 min"}],
            "date": "2026-02-01", "time": "10:00", "period": "Manhã",
        })
        assert r.status_code == 200
        assert r.json()["id"].startswith("AF-")
