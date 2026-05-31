"""Konfiguratsiya — muhit o'zgaruvchilaridan (environment) o'qiladi.

`pydantic-settings` orqali sozlamalar markazlashtiriladi. Maxfiy qiymatlar
(JWT siri, DB URL) faqat muhit o'zgaruvchilari yoki `.env` fayli orqali
beriladi va kodga yozilmaydi.

Bog'liq talablar:
- R2.1: access token 15 daqiqa, refresh token 30 kun.
- R20.5: OpenAPI hujjatlari sozlamasi.
- R18.2: fayl xotirasi (lokal -> S3) abstraksiyasi uchun sozlamalar.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ilova sozlamalari — muhit o'zgaruvchilaridan to'ldiriladi."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Umumiy ilova sozlamalari ---
    app_name: str = "MTT Menejer Diagnostika API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- OpenAPI / docs (R20.5) ---
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    # --- Ma'lumotlar bazasi (PostgreSQL) ---
    database_url: str = (
        "postgresql+psycopg://mtt:mtt@localhost:5432/mtt_diagnostika"
    )

    # --- JWT autentifikatsiya (R2.1, R17.1, R17.2) ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    # Access token 15 daqiqa (R2.1)
    access_token_expire_minutes: int = 15
    # Refresh token 30 kun (R2.1)
    refresh_token_expire_days: int = 30

    # --- Parolni tiklash kodi (R3.1) ---
    password_reset_code_expire_minutes: int = 15

    # --- Login bloklash (R2.7) ---
    max_failed_login_attempts: int = 5
    login_lockout_minutes: int = 15

    # --- Fayl xotirasi (R11, R18.2) ---
    file_storage_backend: str = "local"  # local | s3
    file_storage_dir: str = "./var/uploads"
    max_upload_size_bytes: int = 10_485_760  # 10 MB (R11.4)

    # --- Rate limiting (R17.3) ---
    rate_limit_per_minute: int = 60

    # --- CORS ---
    cors_allow_origins: str = "*"

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug_value(cls, value: object) -> object:
        """`DEBUG` qiymatini kengroq satr formatlaridan bool'ga aylantiradi.

        Ba'zi muhitlarda `DEBUG=release` kabi qiymatlar yuboriladi; bunday holat
        test/import paytida yiqilmasligi uchun `False` sifatida talqin qilinadi.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {
                "1",
                "true",
                "t",
                "yes",
                "y",
                "on",
                "debug",
                "dev",
                "development",
            }:
                return True
            if normalized in {
                "0",
                "false",
                "f",
                "no",
                "n",
                "off",
                "release",
                "prod",
                "production",
            }:
                return False
        return value


@lru_cache
def get_settings() -> Settings:
    """Sozlamalarni keshlangan singleton sifatida qaytaradi."""
    return Settings()


# Modul darajasidagi qulay kirish nuqtasi.
settings = get_settings()
