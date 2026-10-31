"""Limitador de taxa simples, em memória, por processo.

SEGURANÇA (auditoria, item S4): nenhuma rota tinha limite de tentativas —
/auth/send-otp, /auth/verify-otp e /admin/login podiam ser chamadas sem
limite, abrindo espaço para disparo de SMS em massa, força bruta do código
OTP e força bruta da senha do admin. Este módulo cobre essas rotas com um
limitador de janela fixa (fixed window), por IP e por conta.

Limitação conhecida: o contador vive na memória deste processo Python. Com
mais de um worker/instância atrás de um balanceador, cada processo soma sua
própria contagem (o limite efetivo multiplica pelo número de processos).
Para produção com múltiplos workers, troque por um backend compartilhado
(ex.: Redis) antes de depender só deste limite.
"""
import time
from threading import Lock

from fastapi import HTTPException, Request

_hits: dict[tuple[str, str], tuple[float, int]] = {}
_lock = Lock()


def check_rate_limit(bucket: str, key: str, limit: int, window_seconds: float) -> None:
    """Levanta 429 se `key` já fez mais de `limit` chamadas em `bucket`
    dentro dos últimos `window_seconds` segundos."""
    now = time.monotonic()
    bucket_key = (bucket, key)
    with _lock:
        window_start, count = _hits.get(bucket_key, (now, 0))
        if now - window_start >= window_seconds:
            window_start, count = now, 0
        count += 1
        _hits[bucket_key] = (window_start, count)

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
        )


def client_ip(request: Request) -> str:
    """IP de quem conectou direto no processo. Não lê X-Forwarded-For: sem
    uma lista de proxies confiáveis configurada, esse cabeçalho pode ser
    forjado por qualquer cliente que fale direto com o backend (hoje a porta
    8000 fica exposta — ver docker-compose.yml)."""
    return request.client.host if request.client else "desconhecido"
