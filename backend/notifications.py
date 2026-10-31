"""Envio de SMS ao cliente nas mudanças de status do agendamento.

Antes, toda mudança de etapa só gerava um `logger.info` ("[Simulação SMS]")
— nenhum SMS de verdade saía (roadmap: "Notificação real é 100% simulada").

Com as três variáveis TWILIO_* preenchidas (ver backend/.env.example), este
módulo manda o SMS de verdade via Twilio. Sem elas — como fica por padrão
neste projeto de demonstração —, cai no mesmo comportamento simulado de
antes (só loga), para que o fluxo continue funcionando sem custo nem conta
em um provedor real, e para deixar claro no log que a notificação não saiu.
"""
import logging

import httpx

from settings import get_settings

logger = logging.getLogger(__name__)

TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


async def send_sms(phone_e164: str, message: str, *, booking_id: str) -> bool:
    """Envia `message` para `phone_e164`. Retorna True se foi enviado (ou
    simulado), False se o envio real foi tentado e falhou. Nunca levanta
    exceção — uma falha no provedor de SMS não pode derrubar o agendamento.
    """
    settings = get_settings()
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
        # SEGURANÇA (auditoria, item S8): nunca logar o telefone do cliente.
        logger.info("[SMS simulado - provedor não configurado] agendamento %s: %s", booking_id, message)
        return True

    url = TWILIO_API_URL.format(sid=settings.twilio_account_sid)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                data={"To": phone_e164, "From": settings.twilio_from_number, "Body": message},
            )
            response.raise_for_status()
        logger.info("SMS enviado via Twilio para o agendamento %s.", booking_id)
        return True
    except Exception:
        # SEGURANÇA (auditoria, item S8): não logar o corpo da exceção — a
        # resposta de erro da Twilio ecoa o número de telefone ("To").
        logger.warning("Falha ao enviar SMS via Twilio para o agendamento %s.", booking_id)
        return False
