"""Envio de e-mail ao cliente (código de verificação de cadastro e mudanças
de status do agendamento).

Antes, a verificação de cadastro usava o Phone OTP do Supabase Auth e cada
mudança de etapa gerava um SMS (Twilio). Migração para e-mail via SendGrid:
com SENDGRID_API_KEY preenchida (ver backend/.env.example), este módulo manda
o e-mail de verdade. Sem ela — como fica por padrão neste projeto de
demonstração —, cai no mesmo comportamento simulado de antes (só loga), para
que o fluxo continue funcionando sem custo nem conta em um provedor real, e
para deixar claro no log que o e-mail não saiu.

SendGrid exige que o remetente (SENDGRID_FROM_EMAIL) seja verificado —
"Single Sender Verification" (um único e-mail, sem precisar de domínio
próprio) ou um domínio verificado — e só então aceita enviar para qualquer
destinatário.
"""
import asyncio
import logging
from email.utils import parseaddr

from sendgrid import SendGridAPIClient

from settings import get_settings

logger = logging.getLogger(__name__)


def _from_field(raw: str) -> dict:
    # Aceita "Nome <email>" ou só "email" (ver SENDGRID_FROM_EMAIL no
    # .env.example) e converte para o formato {"email": ..., "name": ...}
    # exigido pela API v3 da SendGrid.
    name, email = parseaddr(raw)
    return {"email": email, "name": name} if name else {"email": email}


async def _send(to_email: str, subject: str, html: str, *, log_context: str) -> bool:
    """Envia `html` para `to_email` via SendGrid. Retorna True se foi enviado
    (ou simulado), False se o envio real foi tentado e falhou. Nunca levanta
    exceção — uma falha no provedor de e-mail não pode derrubar o fluxo que a
    chamou (cadastro ou atualização de agendamento)."""
    settings = get_settings()
    if not settings.sendgrid_api_key:
        # SEGURANÇA (auditoria, item S8): nunca logar o e-mail do cliente.
        logger.info("[E-mail simulado - provedor não configurado] %s", log_context)
        return True

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": _from_field(settings.sendgrid_from_email),
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    client = SendGridAPIClient(settings.sendgrid_api_key)
    try:
        response = await asyncio.to_thread(client.send, payload)
        if response.status_code >= 300:
            # SEGURANÇA (auditoria, item S8): não logar o corpo da resposta —
            # pode ecoar o e-mail do destinatário de volta no erro.
            logger.warning(
                "Falha ao enviar e-mail via SendGrid (status %s): %s",
                response.status_code,
                log_context,
            )
            return False
        logger.info("E-mail enviado via SendGrid: %s", log_context)
        return True
    except Exception:
        logger.warning("Falha ao enviar e-mail via SendGrid: %s", log_context)
        return False


async def send_verification_email(email: str, code: str, *, purpose: str = "cadastro") -> bool:
    """Envia o código de verificação de 6 dígitos usado em
    /auth/register/verify-code."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #10b981;">Oficina Fácil</h2>
      <p>Use o código abaixo para confirmar seu {purpose}:</p>
      <p style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #1e293b;">{code}</p>
      <p style="color: #64748b; font-size: 13px;">
        O código expira em 10 minutos. Se você não solicitou isso, ignore este e-mail.
      </p>
    </div>
    """
    return await _send(
        email,
        subject="Seu código de verificação — Oficina Fácil",
        html=html,
        log_context=f"código de verificação ({purpose})",
    )


async def send_status_email(email: str, message: str, *, booking_id: str) -> bool:
    """Envia `message` (mudança de etapa do agendamento) para `email`."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #10b981;">Oficina Fácil</h2>
      <p>Atualização do seu agendamento <strong>{booking_id}</strong>:</p>
      <p style="font-size: 16px; color: #1e293b;">{message}</p>
    </div>
    """
    return await _send(
        email,
        subject=f"Atualização do seu agendamento {booking_id} — Oficina Fácil",
        html=html,
        log_context=f"agendamento {booking_id}",
    )
