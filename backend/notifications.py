"""Envio de e-mail ao cliente (código de verificação de cadastro e mudanças
de status do agendamento).

Antes, a verificação de cadastro usava o Phone OTP do Supabase Auth e cada
mudança de etapa gerava um SMS (Twilio). Migração para e-mail: com
RESEND_API_KEY preenchida (ver backend/.env.example), este módulo manda o
e-mail de verdade via Resend. Sem ela — como fica por padrão neste projeto de
demonstração —, cai no mesmo comportamento simulado de antes (só loga), para
que o fluxo continue funcionando sem custo nem conta em um provedor real, e
para deixar claro no log que o e-mail não saiu.
"""
import asyncio
import logging

import resend

from settings import get_settings

logger = logging.getLogger(__name__)


async def _send(to_email: str, subject: str, html: str, *, log_context: str) -> bool:
    """Envia `html` para `to_email` via Resend. Retorna True se foi enviado
    (ou simulado), False se o envio real foi tentado e falhou. Nunca levanta
    exceção — uma falha no provedor de e-mail não pode derrubar o fluxo que a
    chamou (cadastro ou atualização de agendamento)."""
    settings = get_settings()
    if not settings.resend_api_key:
        # SEGURANÇA (auditoria, item S8): nunca logar o e-mail do cliente.
        logger.info("[E-mail simulado - provedor não configurado] %s", log_context)
        return True

    resend.api_key = settings.resend_api_key
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
        )
        logger.info("E-mail enviado via Resend: %s", log_context)
        return True
    except Exception:
        # SEGURANÇA (auditoria, item S8): não logar o corpo da exceção — a
        # resposta de erro do provedor pode ecoar o e-mail do destinatário.
        logger.warning("Falha ao enviar e-mail via Resend: %s", log_context)
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
