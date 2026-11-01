"""Teste unitário do envio de e-mail (notifications.py) — não precisa de
Supabase nem de conta Resend real, roda sempre. Troca resend.Emails.send por
um fake para não bater na rede."""
import asyncio

import notifications
import settings


class _FakeSettings:
    def __init__(self, resend_api_key="", resend_from_email="Oficina Fácil <onboarding@resend.dev>"):
        self.resend_api_key = resend_api_key
        self.resend_from_email = resend_from_email


class _FakeEmails:
    """Substitui resend.Emails: grava a chamada e nunca abre uma conexão de
    rede."""

    calls = []
    should_fail = False

    @classmethod
    def send(cls, params):
        cls.calls.append(params)
        if cls.should_fail:
            raise RuntimeError("Falha simulada do provedor.")
        return {"id": "fake-email-id"}


def _patch_resend(monkeypatch, should_fail=False):
    _FakeEmails.calls = []
    _FakeEmails.should_fail = should_fail
    monkeypatch.setattr(notifications.resend, "Emails", _FakeEmails)


def test_send_status_email_without_credentials_is_simulated_and_does_not_hit_network(monkeypatch):
    monkeypatch.setattr(notifications, "get_settings", lambda: _FakeSettings())
    _patch_resend(monkeypatch)

    ok = asyncio.run(notifications.send_status_email("cliente@example.com", "Olá!", booking_id="AF-000001"))

    assert ok is True
    assert _FakeEmails.calls == []  # nenhuma chamada à API foi feita


def test_send_status_email_with_credentials_calls_resend(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(resend_api_key="re_test_123")
    )
    _patch_resend(monkeypatch)

    ok = asyncio.run(
        notifications.send_status_email("cliente@example.com", "Seu carro está pronto.", booking_id="AF-000002")
    )

    assert ok is True
    [call] = _FakeEmails.calls
    assert call["to"] == ["cliente@example.com"]
    assert "Seu carro está pronto." in call["html"]
    assert "AF-000002" in call["subject"]


def test_send_status_email_returns_false_without_raising_when_resend_fails(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(resend_api_key="re_test_123")
    )
    _patch_resend(monkeypatch, should_fail=True)

    ok = asyncio.run(notifications.send_status_email("cliente@example.com", "Oi", booking_id="AF-000003"))

    assert ok is False


def test_send_verification_email_includes_code(monkeypatch):
    monkeypatch.setattr(
        notifications, "get_settings", lambda: _FakeSettings(resend_api_key="re_test_123")
    )
    _patch_resend(monkeypatch)

    ok = asyncio.run(notifications.send_verification_email("cliente@example.com", "123456"))

    assert ok is True
    [call] = _FakeEmails.calls
    assert "123456" in call["html"]


def test_settings_default_resend_vars_to_empty_string(monkeypatch):
    # Sem RESEND_API_KEY no ambiente, get_settings() não deve quebrar (as
    # outras variáveis obrigatórias de Supabase continuam exigidas normalmente).
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    settings.get_settings.cache_clear()

    result = settings.get_settings()

    assert result.resend_api_key == ""
    settings.get_settings.cache_clear()
