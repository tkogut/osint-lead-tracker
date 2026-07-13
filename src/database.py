"""
database.py — SQLite via aiosqlite.
Tabela leads z unikalnym URL-em (deduplikacja).
"""

import logging
import os
from datetime import datetime
from typing import Optional

import aiosqlite

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
DB_PATH = settings.sqlite_path


async def init_db() -> None:
    """Tworzy tabelę leads jeśli nie istnieje."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    UNIQUE NOT NULL,
                tytul       TEXT    NOT NULL,
                typ         TEXT,
                lokalizacja TEXT,
                inwestor    TEXT,
                wykonawca   TEXT,
                zakres      TEXT,
                uzasadnienie TEXT,
                priorytet   TEXT,
                data_pub    TEXT,
                odoo_id     INTEGER,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await db.commit()
    logger.info("DB init OK → %s", DB_PATH)


async def url_exists(url: str) -> bool:
    """Sprawdza czy URL jest już w bazie (deduplikacja)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM leads WHERE url = ? LIMIT 1", (url,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def save_lead(lead: dict, odoo_id: Optional[int] = None) -> int:
    """
    Zapisuje leada do SQLite.
    Zwraca rowid nowego rekordu.
    Raises sqlite3.IntegrityError jeśli URL już istnieje.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO leads
                (url, tytul, typ, lokalizacja, inwestor, wykonawca,
                 zakres, uzasadnienie, priorytet, data_pub, odoo_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead.get("url", ""),
                lead.get("tytul", ""),
                lead.get("typ"),
                lead.get("lokalizacja"),
                lead.get("inwestor"),
                lead.get("wykonawca"),
                lead.get("zakres"),
                lead.get("uzasadnienie"),
                lead.get("priorytet"),
                lead.get("data"),
                odoo_id,
                datetime.utcnow().isoformat(),
            ),
        )
        await db.commit()
        logger.info("Saved lead id=%s url=%s", cursor.lastrowid, lead.get("url"))
        return cursor.lastrowid


async def get_recent_leads(limit: int = 50) -> list[dict]:
    """Zwraca ostatnie N leadów (dla endpointu /leads)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
