"""Teste unitário do limitador (rate_limit.py) — não precisa de Supabase
nem de servidor rodando, roda sempre (ver item S4 da auditoria)."""
import time

import pytest
from fastapi import HTTPException

from rate_limit import _hits, check_rate_limit


def test_allows_calls_up_to_the_limit():
    _hits.clear()
    for _ in range(3):
        check_rate_limit("bucket", "key-a", limit=3, window_seconds=60)


def test_blocks_the_call_after_the_limit():
    _hits.clear()
    for _ in range(3):
        check_rate_limit("bucket", "key-b", limit=3, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        check_rate_limit("bucket", "key-b", limit=3, window_seconds=60)
    assert exc.value.status_code == 429


def test_different_keys_have_independent_counters():
    _hits.clear()
    check_rate_limit("bucket", "ip-1", limit=1, window_seconds=60)
    # Outra chave (ex.: outro IP) não é afetada pelo limite da primeira.
    check_rate_limit("bucket", "ip-2", limit=1, window_seconds=60)


def test_different_buckets_have_independent_counters():
    _hits.clear()
    check_rate_limit("send-otp:ip", "same-value", limit=1, window_seconds=60)
    # Mesmo valor de chave, mas rota/propósito diferente: não compartilha contador.
    check_rate_limit("admin-login:ip", "same-value", limit=1, window_seconds=60)


def test_window_resets_after_it_expires():
    _hits.clear()
    check_rate_limit("bucket", "key-c", limit=1, window_seconds=0.05)
    time.sleep(0.06)
    # Janela anterior já expirou: a contagem reinicia.
    check_rate_limit("bucket", "key-c", limit=1, window_seconds=0.05)
