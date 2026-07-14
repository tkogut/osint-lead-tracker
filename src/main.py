"""
main.py — Punkt wejścia FastAPI + APScheduler dla osint-lead-tracker.
Zawiera interfejs API dla modułu Lead Dashboard (Auth, Accounts, Settings, Logs, Sandbox).
"""

import json
import logging
import sqlite3
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Security, status, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_recent_leads, init_db, save_lead, url_exists, AsyncSessionLocal
from odoo_integration import get_odoo_client
from osint_engine import get_engine, get_date_limits
from models import User, Session as UserSession, Account, ResearchLog, Setting
from schemas import LoginRequest, AccountCreate, AccountResponse, SandboxRequest, SettingUpdate
from auth import verify_password, create_user_session, validate_session_token

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
# Security (X-API-Token for external APIs)
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
# Database Session Dependency
# ---------------------------------------------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Authentication Dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    session_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagane logowanie."
        )
    user = await validate_session_token(db, session_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesja wygasła lub jest niepoprawna."
        )
    return user


# ---------------------------------------------------------------------------
# Core pipeline (shared between scheduler and manual trigger)
# ---------------------------------------------------------------------------
async def run_osint_pipeline() -> dict[str, Any]:
    """
    Główna logika wyszukiwania leadów ze wszystkich źródeł.
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

    # Automatyczny start crona
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
    description="Mikroserwis wyszukujący wagi samochodowe (e-Zamówienia, GUNB, Google Search) i integrujący je z Odoo CRM.",
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# HTTP Endpoints - System & Public
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"], summary="Liveness probe")
async def health() -> dict:
    next_run = None
    job = scheduler.get_job("daily_osint")
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {
        "status": "ok",
        "service": "osint-lead-tracker",
        "version": "1.3.0",
        "scheduler": "running" if scheduler.running else "stopped",
        "next_run": next_run,
    }


@app.post("/trigger-osint", tags=["OSINT"], summary="Ręczne uruchomienie skanu (X-API-Token)")
async def trigger_osint(_token: Annotated[str, Depends(verify_token)]) -> dict:
    logger.info("Manual trigger via /trigger-osint")
    stats = await run_osint_pipeline()
    return {"triggered": True, "stats": stats}


@app.get("/leads", tags=["OSINT"], summary="Ostatnie leady (X-API-Token)")
async def list_leads(limit: int = 50, _token: Annotated[str, Depends(verify_token)]) -> dict:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit musi być w zakresie 1–500")
    rows = await get_recent_leads(limit=limit)
    return {"count": len(rows), "leads": rows}


# ---------------------------------------------------------------------------
# API Endpoints - Dashboard Authentication
# ---------------------------------------------------------------------------
@app.post("/api/auth/login", tags=["Auth"])
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == req.username).limit(1))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(req.password, user.salt, user.password_hash):
        raise HTTPException(status_code=401, detail="Niepoprawny login lub hasło.")
        
    token = await create_user_session(db, user.id, ttl_hours=24)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=24 * 3600,
        samesite="lax",
        secure=False  # Ustaw na True na produkcji z HTTPS
    )
    return {"success": True, "username": user.username, "role": user.role}


@app.post("/api/auth/logout", tags=["Auth"])
async def logout(response: Response, session_token: Optional[str] = Cookie(None), db: AsyncSession = Depends(get_db)):
    if session_token:
        await db.execute(delete(UserSession).filter(UserSession.token == session_token))
        await db.commit()
    response.delete_cookie("session_token")
    return {"success": True}


@app.get("/api/auth/me", tags=["Auth"])
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {"username": current_user.username, "role": current_user.role}


# ---------------------------------------------------------------------------
# API Endpoints - Dashboard Accounts (Multi-tenancy CRUD)
# ---------------------------------------------------------------------------
@app.get("/api/accounts", response_model=List[AccountResponse], tags=["Accounts"])
async def get_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Account).order_by(Account.id.asc()))
    accounts = result.scalars().all()
    
    resp = []
    for acc in accounts:
        resp.append(AccountResponse(
            id=acc.id,
            name=acc.name,
            target_cpvs=json.loads(acc.target_cpvs),
            target_keywords=json.loads(acc.target_keywords),
            custom_prompt=acc.custom_prompt,
            llm_model=acc.llm_model,
            llm_temperature=acc.llm_temperature,
            llm_max_tokens=acc.llm_max_tokens,
            odoo_company_id=acc.odoo_company_id,
            odoo_user_id=acc.odoo_user_id,
            odoo_tag_ids=json.loads(acc.odoo_tag_ids),
            odoo_team_id=acc.odoo_team_id,
            odoo_source_id=acc.odoo_source_id,
            is_active=acc.is_active
        ))
    return resp


@app.post("/api/accounts", response_model=AccountResponse, tags=["Accounts"])
async def create_account(
    req: AccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    # Weryfikacja unikalności nazwy
    check_name = await db.execute(select(Account).filter(Account.name == req.name).limit(1))
    if check_name.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Konto o takiej nazwie już istnieje.")

    new_acc = Account(
        name=req.name,
        target_cpvs=json.dumps(req.target_cpvs),
        target_keywords=json.dumps(req.target_keywords),
        custom_prompt=req.custom_prompt,
        llm_model=req.llm_model,
        llm_temperature=req.llm_temperature,
        llm_max_tokens=req.llm_max_tokens,
        odoo_company_id=req.odoo_company_id,
        odoo_user_id=req.odoo_user_id,
        odoo_tag_ids=json.dumps(req.odoo_tag_ids),
        odoo_team_id=req.odoo_team_id,
        odoo_source_id=req.odoo_source_id,
        is_active=req.is_active
    )
    db.add(new_acc)
    await db.commit()
    await db.refresh(new_acc)
    
    return AccountResponse(
        id=new_acc.id,
        name=new_acc.name,
        target_cpvs=json.loads(new_acc.target_cpvs),
        target_keywords=json.loads(new_acc.target_keywords),
        custom_prompt=new_acc.custom_prompt,
        llm_model=new_acc.llm_model,
        llm_temperature=new_acc.llm_temperature,
        llm_max_tokens=new_acc.llm_max_tokens,
        odoo_company_id=new_acc.odoo_company_id,
        odoo_user_id=new_acc.odoo_user_id,
        odoo_tag_ids=json.loads(new_acc.odoo_tag_ids),
        odoo_team_id=new_acc.odoo_team_id,
        odoo_source_id=new_acc.odoo_source_id,
        is_active=new_acc.is_active
    )


@app.put("/api/accounts/{id}", response_model=AccountResponse, tags=["Accounts"])
async def update_account(
    id: int,
    req: AccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Account).filter(Account.id == id).limit(1))
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Konto nie istnieje.")

    acc.name = req.name
    acc.target_cpvs = json.dumps(req.target_cpvs)
    acc.target_keywords = json.dumps(req.target_keywords)
    acc.custom_prompt = req.custom_prompt
    acc.llm_model = req.llm_model
    acc.llm_temperature = req.llm_temperature
    acc.llm_max_tokens = req.llm_max_tokens
    acc.odoo_company_id = req.odoo_company_id
    acc.odoo_user_id = req.odoo_user_id
    acc.odoo_tag_ids = json.dumps(req.odoo_tag_ids)
    acc.odoo_team_id = req.odoo_team_id
    acc.odoo_source_id = req.odoo_source_id
    acc.is_active = req.is_active
    
    await db.commit()
    
    return AccountResponse(
        id=acc.id,
        name=acc.name,
        target_cpvs=json.loads(acc.target_cpvs),
        target_keywords=json.loads(acc.target_keywords),
        custom_prompt=acc.custom_prompt,
        llm_model=acc.llm_model,
        llm_temperature=acc.llm_temperature,
        llm_max_tokens=acc.llm_max_tokens,
        odoo_company_id=acc.odoo_company_id,
        odoo_user_id=acc.odoo_user_id,
        odoo_tag_ids=json.loads(acc.odoo_tag_ids),
        odoo_team_id=acc.odoo_team_id,
        odoo_source_id=acc.odoo_source_id,
        is_active=acc.is_active
    )


@app.delete("/api/accounts/{id}", tags=["Accounts"])
async def delete_account(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Account).filter(Account.id == id).limit(1))
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="Konto nie istnieje.")
    
    await db.delete(acc)
    await db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# API Endpoints - Settings Management
# ---------------------------------------------------------------------------
@app.get("/api/settings", tags=["Settings"])
async def get_settings_list(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Setting).order_by(Setting.key.asc()))
    rows = result.scalars().all()
    # Maskujemy klucze API dla bezpieczeństwa w GUI
    safe_settings = []
    for r in rows:
        val = r.value or ""
        if any(sec in r.key for sec in ["KEY", "PASSWORD", "TOKEN"]) and len(val) > 6:
            val = val[:3] + "..." + val[-3:]
        safe_settings.append({"key": r.key, "value": val})
    return safe_settings


@app.put("/api/settings", tags=["Settings"])
async def update_setting(
    req: SettingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Setting).filter(Setting.key == req.key).limit(1))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Ustawienie nie istnieje.")
    
    # Blokada zapisu zamaskowanych wartości
    if req.value.startswith("...") or "..." in req.value:
        raise HTTPException(status_code=400, detail="Nieprawidłowa wartość klucza API.")

    item.value = req.value
    await db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# API Endpoints - Research Logs (Hard Proof Viewer)
# ---------------------------------------------------------------------------
@app.get("/api/logs", tags=["Logs"])
async def get_research_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    result = await db.execute(
        select(ResearchLog, Account.name)
        .join(Account, Account.id == ResearchLog.account_id)
        .order_by(ResearchLog.timestamp.desc())
        .limit(limit)
    )
    rows = result.all()
    
    resp = []
    for log, acc_name in rows:
        resp.append({
            "id": log.id,
            "account_name": acc_name,
            "timestamp": log.timestamp.isoformat(),
            "source": log.source,
            "query_params": json.loads(log.query_params) if log.query_params else {},
            "raw_response_hash": log.raw_response_hash,
            "response_status_code": log.response_status_code,
            "leads_found_count": log.leads_found_count,
            "leads_created_count": log.leads_created_count,
            "log_text": log.log_text
        })
    return resp


# ---------------------------------------------------------------------------
# API Endpoints - LLM Sandbox
# ---------------------------------------------------------------------------
@app.post("/api/sandbox/test", tags=["Sandbox"])
async def run_sandbox_test(
    req: SandboxRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Testuje dany prompt i surowy tekst bezpośrednio w Gemini.
    """
    from google import genai
    from google.genai import types
    
    # Odczytujemy aktualny klucz API z pliku lub bazy
    api_key = settings.gemini_api_key
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Setting).filter(Setting.key == "GEMINI_API_KEY").limit(1))
            db_key = result.scalar_one_or_none()
            if db_key and db_key.value:
                api_key = db_key.value
    except Exception:
        pass

    try:
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model=req.llm_model,
            contents=req.raw_text,
            config=types.GenerateContentConfig(
                system_instruction=req.prompt,
                temperature=req.llm_temperature,
                max_output_tokens=req.llm_max_tokens,
            )
        )
        return {"success": True, "output": response.text or ""}
    except Exception as exc:
        logger.error("Sandbox test error: %s", exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# SPA Page Router - Static Files serving
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    """Serwuje główny plik HTML panelu Dashboard."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h2>Błąd: Brak pliku index.html we frakcji static.</h2>", status_code=404)

# Rejestracja zasobów statycznych (styles.css, app.js)
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
