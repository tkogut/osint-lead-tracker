"""
database.py — SQLite via SQLAlchemy (wsparcie asynchroniczne i synchroniczne).
Kompatybilne wstecznie z dotychczasową strukturą bazy danych.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from config import get_settings
from models import Base, Lead, Setting

def get_db_setting_sync(key: str, default: str = "") -> str:
    """Odczytuje ustawienie z bazy danych w sposób synchroniczny (dla potoków tła)."""
    with SessionLocal() as session:
        result = session.execute(select(Setting).filter(Setting.key == key).limit(1))
        item = result.scalar_one_or_none()
        if item and item.value is not None:
            return item.value
        return default


logger = logging.getLogger(__name__)
settings = get_settings()

# Ustalenie URL bazodanowych
async_db_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
sync_db_url = settings.database_url

# Asynchroniczny silnik i fabryka sesji (dla FastAPI)
async_engine = create_async_engine(async_db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

# Synchroniczny silnik i fabryka sesji (dla zadań pobocznych)
sync_engine = create_engine(sync_db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def init_db() -> None:
    """Tworzy wszystkie tabele bazy danych, jeśli nie istnieją."""
    import os
    os.makedirs(os.path.dirname(settings.sqlite_path), exist_ok=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB init OK (SQLAlchemy Async) -> %s", settings.sqlite_path)


async def url_exists(url: str) -> bool:
    """Sprawdza czy URL jest już w bazie (deduplikacja)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).filter(Lead.url == url).limit(1))
        lead = result.scalar_one_or_none()
        return lead is not None


async def save_lead(lead_dict: dict, odoo_id: Optional[int] = None) -> int:
    """Zapisuje leada do SQLite."""
    async with AsyncSessionLocal() as session:
        new_lead = Lead(
            url=lead_dict.get("url", ""),
            tytul=lead_dict.get("tytul", ""),
            typ=lead_dict.get("typ"),
            lokalizacja=lead_dict.get("lokalizacja"),
            inwestor=lead_dict.get("inwestor"),
            wykonawca=lead_dict.get("wykonawca"),
            zakres=lead_dict.get("zakres"),
            uzasadnienie=lead_dict.get("uzasadnienie"),
            priorytet=lead_dict.get("priorytet"),
            data_pub=lead_dict.get("data"),
            odoo_id=odoo_id,
            created_at=datetime.utcnow().isoformat()
        )
        session.add(new_lead)
        await session.commit()
        logger.info("Saved lead id=%s url=%s", new_lead.id, new_lead.url)
        return new_lead.id


async def get_recent_leads(limit: int = 50) -> list[dict]:
    """Zwraca ostatnie N leadów w formacie słowników."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Lead).order_by(Lead.created_at.desc()).limit(limit)
        )
        leads = result.scalars().all()
        return [
            {
                "id": l.id,
                "url": l.url,
                "tytul": l.tytul,
                "typ": l.typ,
                "lokalizacja": l.lokalizacja,
                "inwestor": l.inwestor,
                "wykonawca": l.wykonawca,
                "zakres": l.zakres,
                "uzasadnienie": l.uzasadnienie,
                "priorytet": l.priorytet,
                "data_pub": l.data_pub,
                "odoo_id": l.odoo_id,
                "created_at": l.created_at
            }
            for l in leads
        ]
