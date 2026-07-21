"""
config.py — Pydantic Settings dla osint-lead-tracker.
Walidacja zmiennych środowiskowych przy starcie aplikacji.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- AI ---
    gemini_api_key: str

    # --- Odoo XML-RPC ---
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_api_key: str
    odoo_team_id: int = 0
    odoo_source_id: int = 0

    # --- API Security ---
    api_token: str

    # --- Database ---
    database_url: str = "sqlite:///./data/leads.db"
    sqlite_path: str = "./data/leads.db"

    # --- APScheduler & Pipeline ---
    cron_hour: int = 6
    cron_minute: int = 0
    cron_timezone: str = "Europe/Warsaw"
    search_window_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Zwraca skeszowane ustawienia aplikacji."""
    return Settings()  # type: ignore[call-arg]
