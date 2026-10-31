"""Fábricas de clientes Supabase usadas por todo o backend.

Dois clientes, dois propósitos:
  - get_auth_client(): chave anon, usado apenas para operações de autenticação
    "como o usuário" (sign_in_with_otp, verify_otp, sign_in_with_password).
  - get_admin_client(): chave service_role, usado para toda leitura/escrita em
    tabelas (profiles, vehicles, bookings, ...) e para a Admin API do GoTrue
    (criar usuário, validar token, forçar logout). Ela ignora RLS porque o
    backend já fez sua própria checagem de autorização (require_admin) antes
    de usar esse cliente — RLS continua existindo no banco como camada de
    defesa para qualquer acesso direto futuro (ex.: app mobile falando com o
    Supabase sem passar por este backend).
"""
from functools import lru_cache

from supabase import Client, create_client
from settings import get_settings


@lru_cache
def get_admin_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache
def get_auth_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
