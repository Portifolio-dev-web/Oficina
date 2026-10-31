"""Testes de integração do painel admin contra um projeto Supabase real.

Requer supabase_schema.sql + supabase_seed.sql aplicados e o usuário
administrador já criado via backend/scripts/create_admin.py, usando as
mesmas credenciais de ADMIN_EMAIL/ADMIN_PASSWORD definidas em backend/.env.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "monitor.informatica25@gmail.com")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD")

pytestmark = pytest.mark.skipif(
    not (os.environ.get("SUPABASE_URL") and ADMIN_PASS),
    reason=(
        "Requer SUPABASE_URL e ADMIN_PASSWORD, com o usuário administrador "
        "já criado via backend/scripts/create_admin.py."
    ),
)


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
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": "wrong"})
        assert r.status_code == 401

    def test_login_wrong_user(self, client):
        r = client.post(
            f"{API}/admin/login", json={"username": "nobody@example.com", "password": ADMIN_PASS}
        )
        assert r.status_code == 401

    def test_login_success_admin(self, client):
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["token"], str) and len(data["token"]) > 10
        assert data["user"]["username"] == ADMIN_USER

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
        assert data["stats"]["mecanicosTotal"] == len(data["mechanics"])
        assert data["stats"]["mecanicosDisponiveis"] == sum(1 for m in data["mechanics"] if m["available"])


# --- POST /api/admin/mechanics/{id}/toggle (auth required) ---
class TestMechanicToggleAuth:
    def test_toggle_no_token(self, client):
        r = client.post(f"{API}/admin/mechanics/00000000-0000-0000-0000-000000000000/toggle")
        assert r.status_code == 401

    def test_toggle_with_token(self, client, token):
        mechanics = client.get(f"{API}/admin/overview", headers=auth(token)).json()["mechanics"]
        assert mechanics, "Rode supabase_seed.sql para ter mecânicos cadastrados."
        mechanic_id, before = mechanics[0]["id"], mechanics[0]["available"]

        r = client.post(f"{API}/admin/mechanics/{mechanic_id}/toggle", headers=auth(token))
        assert r.status_code == 200
        assert r.json()["available"] == (not before)
        client.post(f"{API}/admin/mechanics/{mechanic_id}/toggle", headers=auth(token))  # restore

    def test_toggle_invalid_id(self, client, token):
        r = client.post(f"{API}/admin/mechanics/not-a-uuid/toggle", headers=auth(token))
        assert r.status_code == 404

    def test_toggle_unknown_uuid(self, client, token):
        r = client.post(
            f"{API}/admin/mechanics/00000000-0000-0000-0000-000000000000/toggle", headers=auth(token)
        )
        assert r.status_code == 404


# --- POST /api/admin/mechanics e DELETE /api/admin/mechanics/{id} (CRUD) ---
class TestMechanicCRUD:
    def test_create_no_token(self, client):
        r = client.post(f"{API}/admin/mechanics", json={"name": "Teste"})
        assert r.status_code == 401

    def test_delete_no_token(self, client):
        r = client.delete(f"{API}/admin/mechanics/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_create_requires_name(self, client, token):
        r = client.post(f"{API}/admin/mechanics", json={"name": "   "}, headers=auth(token))
        assert r.status_code == 400

    def test_create_and_delete(self, client, token):
        r = client.post(
            f"{API}/admin/mechanics",
            json={"name": "Mecânico de Teste", "specialty": "Testes automatizados"},
            headers=auth(token),
        )
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["name"] == "Mecânico de Teste"
        assert created["specialty"] == "Testes automatizados"
        assert created["available"] is True

        overview = client.get(f"{API}/admin/overview", headers=auth(token)).json()
        assert any(m["id"] == created["id"] for m in overview["mechanics"])

        r2 = client.delete(f"{API}/admin/mechanics/{created['id']}", headers=auth(token))
        assert r2.status_code == 200
        assert r2.json()["success"] is True

        overview_after = client.get(f"{API}/admin/overview", headers=auth(token)).json()
        assert not any(m["id"] == created["id"] for m in overview_after["mechanics"])

    def test_delete_invalid_id(self, client, token):
        r = client.delete(f"{API}/admin/mechanics/not-a-uuid", headers=auth(token))
        assert r.status_code == 404

    def test_delete_unknown_uuid(self, client, token):
        r = client.delete(
            f"{API}/admin/mechanics/00000000-0000-0000-0000-000000000000", headers=auth(token)
        )
        assert r.status_code == 404


# --- POST /api/admin/logout ---
# Nota: diferente do mock antigo (token em um set em memória, removido no
# logout), o access token aqui é um JWT stateless do Supabase Auth — ele
# permanece criptograficamente válido até expirar, mesmo após o logout
# revogar a sessão no GoTrue. Por isso este teste verifica apenas que o
# endpoint funciona, sem assumir invalidação imediata do token corrente.
class TestAdminLogout:
    def test_logout_ok(self, client):
        r = client.post(f"{API}/admin/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        tok = r.json()["token"]
        assert client.get(f"{API}/admin/overview", headers=auth(tok)).status_code == 200
        r2 = client.post(f"{API}/admin/logout", headers=auth(tok))
        assert r2.status_code == 200
        assert r2.json()["success"] is True
