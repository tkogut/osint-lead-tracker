"""
seed.py — Skrypt do inicjalizacji danych startowych i migracji (Użytkownicy, Ustawienia, Domena).
"""

import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import init_db, AsyncSessionLocal
from models import User, Account, Setting
from auth import generate_salt, hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def seed_data() -> None:
    """Inicjalizuje bazę danych domyślnymi rekordami jeśli jest pusta."""
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # 1. Inicjalizacja Domyślnego Administratora
        user_check = await session.execute(select(User).limit(1))
        if not user_check.scalar_one_or_none():
            logger.info("Tworzenie domyślnego konta administratora (admin/admin)...")
            salt = generate_salt()
            pwd_hash = hash_password("admin", salt)
            
            admin_user = User(
                username="admin",
                password_hash=pwd_hash,
                salt=salt,
                role="admin"
            )
            session.add(admin_user)
            await session.commit()
            logger.info("Utworzono użytkownika: admin")
            
        # 2. Inicjalizacja Domyślnego Konta Researchu (Campaign)
        account_check = await session.execute(select(Account).limit(1))
        if not account_check.scalar_one_or_none():
            logger.info("Tworzenie domyślnego konta researchu (Wagi Samochodowe)...")
            default_account = Account(
                name="Wagi Samochodowe",
                target_cpvs=json.dumps(["42923110-6", "42923000-2", "42923200-0"]),
                target_keywords=json.dumps(["waga", "wagi", "najazdowa", "samochodowa"]),
                custom_prompt=None,
                llm_model="gemini-2.5-flash",
                llm_temperature=0.1,
                llm_max_tokens=4096,
                odoo_company_id=1,      # Multicompany Company ID
                odoo_user_id=None,      # Opcjonalny handlowiec (None)
                odoo_tag_ids=json.dumps([]),
                odoo_team_id=settings.odoo_team_id or 0,
                odoo_source_id=settings.odoo_source_id or 0,
                is_active=True
            )
            session.add(default_account)
            await session.commit()
            logger.info("Utworzono domyślne konto: Wagi Samochodowe")
            
        setting_keys = [
            "GEMINI_API_KEY",
            "ODOO_URL",
            "ODOO_DB",
            "ODOO_USER",
            "ODOO_API_KEY",
            "API_TOKEN",
            "CRON_HOUR",
            "CRON_MINUTE",
            "CRON_TIMEZONE",
            "SEARCH_WINDOW_DAYS",
            "SCRAPER_AUTOMATYKA_USER",
            "SCRAPER_AUTOMATYKA_PASS",
            "SCRAPER_LOGINTRADE_USER",
            "SCRAPER_LOGINTRADE_PASS"
        ]
        
        for key in setting_keys:
            check_setting = await session.execute(
                select(Setting).filter(Setting.key == key).limit(1)
            )
            if not check_setting.scalar_one_or_none():
                # Pobieramy wartość z pydantic settings
                val = ""
                if key == "GEMINI_API_KEY": val = settings.gemini_api_key
                elif key == "ODOO_URL": val = settings.odoo_url
                elif key == "ODOO_DB": val = settings.odoo_db
                elif key == "ODOO_USER": val = settings.odoo_user
                elif key == "ODOO_API_KEY": val = settings.odoo_api_key
                elif key == "API_TOKEN": val = settings.api_token
                elif key == "CRON_HOUR": val = str(settings.cron_hour)
                elif key == "CRON_MINUTE": val = str(settings.cron_minute)
                elif key == "CRON_TIMEZONE": val = settings.cron_timezone
                elif key == "SEARCH_WINDOW_DAYS": val = "7"

                
                db_setting = Setting(key=key, value=val)
                session.add(db_setting)
                
        await session.commit()
        logger.info("Synchronizacja ustawień globalnych ukończona.")


if __name__ == "__main__":
    asyncio.run(seed_data())
