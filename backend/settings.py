"""Leitura centralizada das variáveis de ambiente do backend."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    admin_username: str
    admin_email: str
    cors_origins: list[str]


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variável de ambiente {name} não definida. Configure backend/.env "
            f"com as credenciais do seu projeto Supabase (veja backend/.env.example)."
        )
    return value


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=_require("SUPABASE_URL"),
        supabase_anon_key=_require("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_require("SUPABASE_SERVICE_ROLE_KEY"),
        admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
        admin_email=os.environ.get("ADMIN_EMAIL", "monitor.informatica25@gmail.com"),
        cors_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    )
