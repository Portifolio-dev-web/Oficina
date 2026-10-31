"""Teste unitário do envio de SMS (notifications.py) — não precisa de
Supabase nem de conta Twilio real, roda sempre (roadmap: "Notificação
real"). Usa um httpx.AsyncClient falso para não bater na rede."""
import asyncio

import pytest

import notifications
import settings


class _FakeSettings:
    def __init__(self, sid="", token="", from_number=""):
        self.twilio_account_sid = sid
        self.twilio_auth_token = token
        self.twilio_from_number = from_number


class _FakeResponse:
    def __init__(self, status_code=201):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeAsyncClient:
    """Substitui httpx.AsyncClient: grava a chamada e devolve uma resposta
    fixa, sem abrir nenhuma conexão de rede."""

    instances = []

    def __init__(self, *args, **kwargs):
        self.post_calls = []
        _FakeAsyncClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.post_calls.append({"url": url, **kwargs})
        return _FakeResponse(_FakeAsyncClient.next_status)


def _patch_twilio_client(monkeypatch, status_code=201):
    _FakeAsyncClient.instances = []
    _FakeAsyncClient.next_status = status_code
    monkeypatch.setattr(notifications.httpx, "AsyncClient", _FakeAsyncClient)


def test_send_sms_without_credentials_is_simulated_and_does_not_hit_network(monkeypatch):
    monkeypatch.setattr(notifications, "get_settings", lambda: _FakeSettings())
    _patch_twilio_client(monkeypatch)

    ok = asyncio.run(notifications.send_sms("+5511999998888", "Olá!", booking_id="AF-000001"))

    assert ok is True
    assert _FakeAsyncClient.instances == []  # nenhuma chamada HTTP foi feita


def test_send_sms_with_credentials_calls_twilio(monkeypatch):
    monkeypatch.setattr(
        notifications,
        "get_settings",
        lambda: _FakeSettings(sid="ACxxx", token="tok", from_number="+15017122661"),
    )
    _patch_twilio_client(monkeypatch, status_code=201)

    ok = asyncio.run(notifications.send_sms("+5511999998888", "Seu carro está pronto.", booking_id="AF-000002"))

    assert ok is True
    [client] = _FakeAsyncClient.instances
    [call] = client.post_calls
    assert call["url"] == "https://api.twilio.com/2010-04-01/Accounts/ACxxx/Messages.json"
    assert call["auth"] == ("ACxxx", "tok")
    assert call["data"] == {
        "To": "+5511999998888",
        "From": "+15017122661",
        "Body": "Seu carro está pronto.",
    }


def test_send_sms_returns_false_without_raising_when_twilio_fails(monkeypatch):
    monkeypatch.setattr(
        notifications,
        "get_settings",
        lambda: _FakeSettings(sid="ACxxx", token="tok", from_number="+15017122661"),
    )
    _patch_twilio_client(monkeypatch, status_code=400)

    ok = asyncio.run(notifications.send_sms("+5511999998888", "Oi", booking_id="AF-000003"))

    assert ok is False


def test_settings_default_twilio_vars_to_empty_string(monkeypatch):
    # Sem TWILIO_* no ambiente, get_settings() não deve quebrar (as outras
    # variáveis obrigatórias de Supabase continuam exigidas normalmente).
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM_NUMBER", raising=False)
    settings.get_settings.cache_clear()

    result = settings.get_settings()

    assert result.twilio_account_sid == ""
    assert result.twilio_auth_token == ""
    assert result.twilio_from_number == ""
    settings.get_settings.cache_clear()
