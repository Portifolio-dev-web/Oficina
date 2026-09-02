"""Admin dashboard API tests for AutoFix Pro."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://shop-scheduling-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- GET /api/admin/overview ---
class TestAdminOverview:
    def test_overview_shape_and_seeds(self, client):
        r = client.get(f"{API}/admin/overview")
        assert r.status_code == 200
        data = r.json()
        for k in ("stats", "appointments", "mechanics", "services"):
            assert k in data
        stats = data["stats"]
        for k in ("total", "emManutencao", "aguardando", "prontos", "mecanicosDisponiveis", "mecanicosTotal"):
            assert k in stats
        # 6 seeded appts, 5 mechanics
        assert stats["total"] >= 6
        assert stats["mecanicosTotal"] == 5
        assert len(data["mechanics"]) == 5
        # AF-DEMO ids present
        ids = [a["id"] for a in data["appointments"]]
        for i in range(1, 7):
            assert f"AF-DEMO{i:02d}" in ids
        # Consistency: sum of buckets can't exceed total
        assert stats["emManutencao"] + stats["aguardando"] + stats["prontos"] <= stats["total"]
        # Services list has name/count/duration
        assert len(data["services"]) > 0
        for s in data["services"]:
            assert "name" in s and "count" in s and "duration" in s


# --- POST /api/admin/mechanics/{id}/toggle ---
class TestMechanicToggle:
    def test_toggle_persists(self, client):
        overview = client.get(f"{API}/admin/overview").json()
        m1_before = next(m for m in overview["mechanics"] if m["id"] == "m1")
        before = m1_before["available"]

        r = client.post(f"{API}/admin/mechanics/m1/toggle")
        assert r.status_code == 200
        assert r.json()["available"] == (not before)

        overview2 = client.get(f"{API}/admin/overview").json()
        m1_after = next(m for m in overview2["mechanics"] if m["id"] == "m1")
        assert m1_after["available"] == (not before)

        # Toggle back to restore state
        client.post(f"{API}/admin/mechanics/m1/toggle")
        overview3 = client.get(f"{API}/admin/overview").json()
        m1_restored = next(m for m in overview3["mechanics"] if m["id"] == "m1")
        assert m1_restored["available"] == before

    def test_toggle_invalid(self, client):
        r = client.post(f"{API}/admin/mechanics/does-not-exist/toggle")
        assert r.status_code == 404


# --- POST /api/tracking/{id}/status advances stage + SMS ---
class TestStatusUpdate:
    def test_advance_appends_sms_and_updates_stats(self, client):
        appt_id = "AF-DEMO04"  # seeded at stage 0
        before_appt = client.get(f"{API}/tracking/{appt_id}").json()
        before_stage = before_appt["statusIndex"]
        before_sms = len(before_appt["smsLogs"])
        before_stats = client.get(f"{API}/admin/overview").json()["stats"]

        r = client.post(f"{API}/tracking/{appt_id}/status", json={"stage": before_stage + 1})
        assert r.status_code == 200
        updated = r.json()
        assert updated["statusIndex"] == before_stage + 1
        assert len(updated["smsLogs"]) == before_sms + 1

        after_stats = client.get(f"{API}/admin/overview").json()["stats"]
        # If it moved from stage 0 -> 1, aguardando should drop by 1 & emManutencao +1
        if before_stage == 0:
            assert after_stats["aguardando"] == before_stats["aguardando"] - 1
            assert after_stats["emManutencao"] == before_stats["emManutencao"] + 1

        # Regress back to restore state
        client.post(f"{API}/tracking/{appt_id}/status", json={"stage": before_stage})

    def test_status_invalid_id(self, client):
        r = client.post(f"{API}/tracking/NO-SUCH/status", json={"stage": 1})
        assert r.status_code == 404
