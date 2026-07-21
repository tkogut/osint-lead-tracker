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
from models import Base, Lead, Setting, PromptVersion

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
    import sqlite3 as _sqlite3
    os.makedirs(os.path.dirname(settings.sqlite_path), exist_ok=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB init OK (SQLAlchemy Async) -> %s", settings.sqlite_path)

    # Idempotent SQLite column migrations (Phase 5)
    try:
        _db_path = settings.sqlite_path
        _con = _sqlite3.connect(_db_path)
        _cur = _con.cursor()
        # Create prompt_versions table if not exists (fallback)
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                version INTEGER NOT NULL DEFAULT 1,
                prompt_text TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        """)
        # Create run_performance_snapshots table
        _cur.execute("""
            CREATE TABLE IF NOT EXISTS run_performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                source VARCHAR(50) NOT NULL,
                run_date VARCHAR(10) NOT NULL,
                leads_generated INTEGER NOT NULL DEFAULT 0,
                grounding_chunks_count INTEGER NOT NULL DEFAULT 0,
                grounding_queries_count INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                api_errors INTEGER NOT NULL DEFAULT 0,
                circuit_breaker_triggered BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            )
        """)
        for _sql in [
            "ALTER TABLE leads ADD COLUMN status VARCHAR(50) DEFAULT 'new'",
            "ALTER TABLE leads ADD COLUMN prompt_version_id INTEGER REFERENCES prompt_versions(id)",
            "ALTER TABLE leads ADD COLUMN last_synced_at DATETIME",
            "ALTER TABLE leads ADD COLUMN pending_approval BOOLEAN DEFAULT 0",
            "ALTER TABLE research_logs ADD COLUMN grounding_chunks_count INTEGER DEFAULT 0",
            "ALTER TABLE research_logs ADD COLUMN grounding_queries_count INTEGER DEFAULT 0",
            "ALTER TABLE research_logs ADD COLUMN input_tokens INTEGER DEFAULT 0",
            "ALTER TABLE research_logs ADD COLUMN output_tokens INTEGER DEFAULT 0",
            "ALTER TABLE accounts ADD COLUMN enabled_sources TEXT DEFAULT '[\"BZP\", \"Google\", \"GUNB\"]'",
        ]:
            try:
                _cur.execute(_sql)
                logger.info("Migration OK: %s", _sql[:60])
            except _sqlite3.OperationalError as _oe:
                if "duplicate column name" in str(_oe):
                    pass  # idempotent
                else:
                    logger.warning("Migration warning: %s", _oe)
        _con.commit()
        _con.close()
    except Exception as _e:
        logger.error("Phase 5 migration error: %s", _e)


async def url_exists(url: str) -> bool:
    """Sprawdza czy URL jest już w bazie (deduplikacja)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).filter(Lead.url == url).limit(1))
        lead = result.scalar_one_or_none()
        return lead is not None


async def save_lead(lead_dict: dict, odoo_id: Optional[int] = None, prompt_version_id: Optional[int] = None, pending_approval: bool = False) -> int:
    """Zapisuje leada do SQLite."""
    async with AsyncSessionLocal() as session:
        # Map alternate keys returned by custom prompts
        tytul = lead_dict.get("tytul") or lead_dict.get("tytul_generowany") or lead_dict.get("nazwa_inwestycji") or ""
        inwestor = lead_dict.get("inwestor") or lead_dict.get("nazwa_inwestora") or ""
        zakres = lead_dict.get("zakres") or lead_dict.get("opis_szczegolowy") or ""
        uzasadnienie = lead_dict.get("uzasadnienie") or lead_dict.get("potencjal_handlowy") or ""
        data_pub = lead_dict.get("data") or lead_dict.get("termin_skladania") or lead_dict.get("data_pub") or ""

        new_lead = Lead(
            url=lead_dict.get("url", ""),
            tytul=tytul,
            typ=lead_dict.get("typ"),
            lokalizacja=lead_dict.get("lokalizacja"),
            inwestor=inwestor,
            wykonawca=lead_dict.get("wykonawca"),
            zakres=zakres,
            uzasadnienie=uzasadnienie,
            priorytet=lead_dict.get("priorytet"),
            data_pub=data_pub,
            odoo_id=odoo_id,
            prompt_version_id=prompt_version_id,
            pending_approval=pending_approval,
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
                "status": l.status,
                "created_at": l.created_at
            }
            for l in leads
        ]
