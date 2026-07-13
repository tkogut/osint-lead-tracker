"""
main.py — Punkt wejścia FastAPI + APScheduler dla osint-lead-tracker.

Endpointy:
  GET  /health            — liveness probe
  POST /trigger-osint     — ręczne uruchomienie (token required)
  GET  /leads             — ostatnie N leadów z SQLite
"""

import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config import get_settings
from database import get_recent_leads, init_db, save_lead, url_exists
from odoo_integration import get_odoo_client
from osint_engine import get_engine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Settings & scheduler
# ---------------------------------------------------------------------------
settings = get_settings()
scheduler = AsyncIOScheduler(timezone=settings.cron_timezone)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=True)


async def verify_token(
    token: Annotated[str, Security(api_key_header)],
) -> str:
    if token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )
    return token


# ---------------------------------------------------------------------------
# Core pipeline (shared between scheduler and manual trigger)
# ---------------------------------------------------------------------------
async def run_osint_pipeline() -> dict[str, Any]:
    """
    Główna logika:
    1. Zapytaj AI → lista leadów
    2. Dla każdego leada sprawdź duplikat w SQLite
    3. Zapisz do SQLite
    4. Stwórz szansę w Odoo
    """
    logger.info("=== OSINT Pipeline START ===")
    engine = get_engine()
    odoo = get_odoo_client()

    leads = engine.run_search()

    stats = {"found": len(leads), "new": 0, "duplicates": 0, "odoo_ok": 0, "odoo_fail": 0}

    for lead in leads:
        url = lead.get("url", "").strip()
        if not url:
            logger.warning("Lead bez URL — pomijam: %s", lead.get("tytul"))
            continue

        # --- deduplikacja ---
        if await url_exists(url):
            logger.info("Duplikat → pomijam: %s", url)
            stats["duplicates"] += 1
            continue

        # --- zapis do Odoo ---
        odoo_id: int | None = None
        try:
            odoo_id = odoo.create_lead(lead)
            if odoo_id:
                stats["odoo_ok"] += 1
                logger.info("Odoo OK → lead_id=%s", odoo_id)
            else:
                stats["odoo_fail"] += 1
        except Exception as exc:
            logger.error("Odoo exception: %s", exc)
            stats["odoo_fail"] += 1

        # --- zapis do SQLite ---
        try:
            await save_lead(lead, odoo_id=odoo_id)
            stats["new"] += 1
        except sqlite3.IntegrityError:
            # race condition: inny worker zapisał ten sam URL
            logger.warning("Integrity error (race) dla URL: %s", url)
            stats["duplicates"] += 1

    logger.info("=== OSINT Pipeline DONE | stats=%s ===", stats)
    return stats


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    await init_db()

    trigger = CronTrigger(
        hour=settings.cron_hour,
        minute=settings.cron_minute,
        timezone=settings.cron_timezone,
    )
    scheduler.add_job(
        run_osint_pipeline,
        trigger=trigger,
        id="daily_osint",
        name="Daily OSINT scan",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — cron=%02d:%02d %s",
        settings.cron_hour,
        settings.cron_minute,
        settings.cron_timezone,
    )

    yield

    # --- shutdown ---
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OSINT Lead Tracker",
    description=(
        "Mikroserwis codziennie skanujący przetargi na wagi samochodowe "
        "i przekazujący leady do Odoo CRM."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["System"],
    summary="Liveness probe",
    response_model=dict,
)
async def health() -> dict:
    """Zwraca status aplikacji i harmonogram następnego uruchomienia."""
    next_run = None
    job = scheduler.get_job("daily_osint")
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {
        "status": "ok",
        "service": "osint-lead-tracker",
        "version": "1.0.0",
        "scheduler": "running" if scheduler.running else "stopped",
        "next_run": next_run,
    }


@app.post(
    "/trigger-osint",
    tags=["OSINT"],
    summary="Ręczne uruchomienie skanu OSINT (wymaga tokenu)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_osint(
    _token: Annotated[str, Depends(verify_token)],
) -> dict:
    """
    Wymusza natychmiastowe uruchomienie pipelinu OSINT.
    Zabezpieczone nagłówkiem X-API-Token.
    """
    logger.info("Manual trigger via /trigger-osint")
    stats = await run_osint_pipeline()
    return {"triggered": True, "stats": stats}


@app.get(
    "/leads",
    tags=["OSINT"],
    summary="Ostatnie leady z bazy SQLite",
    dependencies=[Depends(verify_token)],
)
async def list_leads(limit: int = 50) -> dict:
    """Zwraca ostatnie N leadów zapisanych w SQLite."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit musi być w zakresie 1–500")
    rows = await get_recent_leads(limit=limit)
    return {"count": len(rows), "leads": rows}
