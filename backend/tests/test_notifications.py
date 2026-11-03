"""Teste unitário do envio de e-mail (notifications.py) — não precisa de
Supabase nem de conta SendGrid real, roda sempre. Troca SendGridAPIClient por
um fake para não bater na rede."""
import asyncio

import notifications
import settings


class _FakeSettings:
    def __init__(self, sendgrid_api_key="", sendgrid_from_email="Oficina Fácil <naoresponda@example.com>"):
        self.sendgrid_api_key = sendgrid_api_key
        self.sendgrid_from_email = sendgrid_from_email


class _FakeResponse:
    def __init__(self, status_code=202):
        self.status_code = status_code


class _FakeSendGridClient:
    """Substitui SendGridAPIClient: grava a chamada e nunca abre uma conexão
    de rede."""

    calls = []
    should_fail = False
    next_status = 202

    def __init__(self, api_key):
        self.api_key = api_key

    def send(self, payload):
        _FakeSendGridClient.calls.append(payload)
        if _FakeSendGridClient.should_fail:
            raise RuntimeError("Falha simulada do provedor.")
        return _FakeResponse(_FakeSendGridClient.next_status)


def _patch_sendgrid(monkeypatch, should_fail=False, status_code=202):
    _FakeSendGridClient.calls = []
    _FakeSendGridClient.should_fail = should_fail
    _FakeSendGridClient.next_status = status_code
    monkeypatch.setattr(notifications, "SendGridAPIClient", _FakeSendGridClient)


def test_send_status_email_without_credentials_is_simulated_and_does_not_hit_network(monkeypatch):
    monkeypatch.setattr(notifications, "get_settings", lambda: _FakeSettings())
    _patch_sendgrid(monkeypatch)

    ok = asyncio.run(notifications.send_status_email("cliente@example.com", "Olá!", booking_id="AF-000001"))

    assert ok is True
    assert _FakeSendGridClient.calls == []  # nenhuma chamada à API foi feita


def test_send_status_email_with_credentials_calls_sendgrid(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(sendgrid_api_key="SG.test_123")
    )
    _patch_sendgrid(monkeypatch)

    ok = asyncio.run(
        notifications.send_status_email("cliente@example.com", "Seu carro está pronto.", booking_id="AF-000002")
    )

    assert ok is True
    [call] = _FakeSendGridClient.calls
    assert call["personalizations"] == [{"to": [{"email": "cliente@example.com"}]}]
    assert call["from"] == {"email": "naoresponda@example.com", "name": "Oficina Fácil"}
    assert "Seu carro está pronto." in call["content"][0]["value"]
    assert "AF-000002" in call["subject"]


def test_send_status_email_returns_false_without_raising_when_sendgrid_fails(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(sendgrid_api_key="SG.test_123")
    )
    _patch_sendgrid(monkeypatch, should_fail=True)

    ok = asyncio.run(notifications.send_status_email("cliente@example.com", "Oi", booking_id="AF-000003"))

    assert ok is False


def test_send_status_email_returns_false_on_non_2xx_status(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(sendgrid_api_key="SG.test_123")
    )
    _patch_sendgrid(monkeypatch, status_code=403)

    ok = asyncio.run(notifications.send_status_email("cliente@example.com", "Oi", booking_id="AF-000004"))

    assert ok is False


def test_send_verification_email_includes_code(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(sendgrid_api_key="SG.test_123")
    )
    _patch_sendgrid(monkeypatch)

    ok = asyncio.run(notifications.send_verification_email("cliente@example.com", "123456"))

    assert ok is True
    [call] = _FakeSendGridClient.calls
    assert "123456" in call["content"][0]["value"]


def test_settings_default_sendgrid_vars_to_empty_string(monkeypatch):
    # Sem SENDGRID_API_KEY no ambiente, get_settings() não deve quebrar (as
    # outras variáveis obrigatórias de Supabase continuam exigidas normalmente).
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    settings.get_settings.cache_clear()

    result = settings.get_settings()

    assert result.sendgrid_api_key == ""
    settings.get_settings.cache_clear()
