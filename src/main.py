"""
main.py — Punkt wejścia FastAPI + APScheduler dla osint-lead-tracker.
Zawiera interfejs API dla modułu Lead Dashboard (Auth, Accounts, Settings, Logs, Sandbox).
Wspiera Fazu 2 (Engine Parameterization, Option A Scheduler w Dockerze, wielofirmowość Odoo).
"""

import asyncio
import json
import logging
import sqlite3
import os
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Security, status, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, func, Integer as SAInteger, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from config import get_settings
from database import get_recent_leads, init_db, save_lead, url_exists, AsyncSessionLocal, get_db_setting_sync
from odoo_integration import get_odoo_client
from osint_engine import get_engine, get_date_limits, get_system_instruction
from models import User, Session as UserSession, Account, ResearchLog, Setting, PromptVersion, Lead
from schemas import LoginRequest, AccountCreate, AccountResponse, SandboxRequest, SettingUpdate, ChangePasswordRequest
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
    # Weryfikacja tokena z bazy (lub fallback do config)
    api_token = get_db_setting_sync("API_TOKEN", settings.api_token)
    if token != api_token:
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


api_key_header_optional = APIKeyHeader(name="X-API-Token", auto_error=False)


async def verify_token_or_session(
    token: Annotated[Optional[str], Security(api_key_header_optional)] = None,
    session_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> str:
    if session_token:
        user = await validate_session_token(db, session_token)
        if user:
            return "session_auth"
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagany token API lub aktywna sesja.",
        )
        
    api_token = get_db_setting_sync("API_TOKEN", settings.api_token)
    if token != api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )
    return token


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
    Uruchamia wyszukiwanie dla wszystkich aktywnych kont (kampanii).
    Zapisuje wyniki do bazy danych, logi (ResearchLog) i przekazuje leady do Odoo.
    """
    logger.info("=== OSINT Pipeline START (Multi-tenancy Faza 2) ===")
    
    engine = get_engine()
    odoo = get_odoo_client()
    
    stats = {
        "accounts_scanned": 0,
        "leads_found": 0,
        "leads_new": 0,
        "odoo_ok": 0,
        "odoo_fail": 0
    }
    
    async with AsyncSessionLocal() as session:
        # Pobieramy aktywne konta
        result = await session.execute(select(Account).filter(Account.is_active == True))
        accounts = result.scalars().all()
        
        for account in accounts:
            logger.info("Skanowanie dla konta: %s (ID: %s)", account.name, account.id)
            stats["accounts_scanned"] += 1

            # Resolve aktywnej wersji promptu dla konta (BUG-002 fix)
            pv_result = await session.execute(
                select(PromptVersion.id)
                .filter(PromptVersion.account_id == account.id)
                .order_by(PromptVersion.version.desc())
                .limit(1)
            )
            active_prompt_version_id = pv_result.scalar_one_or_none()
            
            # Pobieramy wyniki wyszukiwania (słownik z podziałem na źródła) - nieblokująco dla Event Loop
            search_results = await asyncio.to_thread(engine.run_search_for_account, account)
            
            for source, (leads, status_code, response_hash) in search_results.items():
                leads_found_count = len(leads)
                leads_created_count = 0
                
                # Zapisujemy parametry zapytania
                query_params = {
                    "cpvs": json.loads(account.target_cpvs),
                    "keywords": json.loads(account.target_keywords)
                }
                
                for lead in leads:
                    url = lead.get("url", "").strip()
                    if not url:
                        continue
                        
                    # Deduplikacja w SQLite
                    if await url_exists(url):
                        logger.info("[%s] Duplikat URL pomijam: %s", source, url)
                        continue
                        
                    # Zapis do Odoo - nieblokująco dla Event Loop
                    odoo_id = None
                    try:
                        # Przekazujemy parametry z konta
                        odoo_id = await asyncio.to_thread(
                            odoo.create_lead,
                            lead,
                            company_id=account.odoo_company_id,
                            user_id=account.odoo_user_id,
                            tag_ids=json.loads(account.odoo_tag_ids),
                            team_id=account.odoo_team_id,
                            source_id=account.odoo_source_id
                        )
                        if odoo_id:
                            stats["odoo_ok"] += 1
                            logger.info("[%s] Odoo OK → id=%s", source, odoo_id)
                        else:
                            stats["odoo_fail"] += 1
                    except Exception as exc:
                        logger.error("[%s] Błąd Odoo: %s", source, exc)
                        stats["odoo_fail"] += 1
                        
                    # Zapis do SQLite
                    try:
                        await save_lead(lead, odoo_id=odoo_id, prompt_version_id=active_prompt_version_id)
                        leads_created_count += 1
                        stats["leads_new"] += 1
                    except IntegrityError:
                        logger.warning("[%s] IntegrityError dla URL: %s", source, url)
                        
                stats["leads_found"] += leads_found_count
                
                # Zapis twardego dowodu w ResearchLog
                log_entry = ResearchLog(
                    account_id=account.id,
                    timestamp=datetime.utcnow(),
                    source=source,
                    query_params=json.dumps(query_params),
                    raw_response_hash=response_hash,
                    response_status_code=status_code,
                    leads_found_count=leads_found_count,
                    leads_created_count=leads_created_count,
                    log_text=f"Skanowanie ukończone. Znaleziono {leads_found_count} leadów, zapisano {leads_created_count}."
                )
                session.add(log_entry)
                
            await session.commit()
            
    logger.info("=== OSINT Pipeline DONE | stats=%s ===", stats)
    return stats


async def sync_lead_statuses() -> dict:
    """Synchronizuje statusy leadów z Odoo CRM."""
    logger.info("=== Odoo Lead Status Sync START ===")
    odoo = get_odoo_client()
    synced = 0
    errors = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Lead).filter(
                Lead.odoo_id.isnot(None),
                Lead.status.notin_(['won', 'lost'])
            )
        )
        leads = result.scalars().all()
        for lead in leads:
            try:
                data = await asyncio.to_thread(
                    odoo.get_lead_status, lead.odoo_id
                )
                if data:
                    prob = data.get('probability', 0)
                    active = data.get('active', True)
                    if prob == 100:
                        lead.status = 'won'
                    elif not active and prob == 0:
                        lead.status = 'lost'
                    elif active and prob > 0:
                        lead.status = 'in_progress'
                    lead.last_synced_at = datetime.utcnow()
                    synced += 1
            except Exception as e:
                logger.error("Lead sync error id=%s: %s", lead.id, e)
                errors += 1
        await session.commit()
    logger.info("=== Odoo Lead Status Sync DONE synced=%s errors=%s ===", synced, errors)
    return {"synced": synced, "errors": errors}


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    await init_db()

    # Odczytujemy konfigurację crona z bazy (lub fallback do config)
    cron_hour = int(get_db_setting_sync("CRON_HOUR", str(settings.cron_hour)))
    cron_minute = int(get_db_setting_sync("CRON_MINUTE", str(settings.cron_minute)))
    cron_tz = get_db_setting_sync("CRON_TIMEZONE", settings.cron_timezone)

    # Automatyczny start crona
    trigger = CronTrigger(
        hour=cron_hour,
        minute=cron_minute,
        timezone=cron_tz,
    )
    scheduler.add_job(
        run_osint_pipeline,
        trigger=trigger,
        id="daily_osint",
        name="Daily OSINT scan",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        sync_lead_statuses,
        CronTrigger(hour=7, minute=0, timezone=settings.cron_timezone),
        id='odoo_sync',
        replace_existing=True
    )
    scheduler.start()
    logger.info(
        "Scheduler started — cron=%02d:%02d %s",
        cron_hour,
        cron_minute,
        cron_tz,
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


@app.post("/trigger-osint", tags=["OSINT"], summary="Ręczne uruchomienie skanu (X-API-Token / Sesja)")
async def trigger_osint(_token: Annotated[str, Depends(verify_token_or_session)]) -> dict:
    logger.info("Manual trigger via /trigger-osint")
    stats = await run_osint_pipeline()
    return {"triggered": True, "stats": stats}


@app.get("/leads", tags=["OSINT"], summary="Ostatnie leady (X-API-Token)")
async def list_leads(_token: Annotated[str, Depends(verify_token)], limit: int = 50) -> dict:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit musi być w zakresie 1–500")
    rows = await get_recent_leads(limit=limit)
    return {"count": len(rows), "leads": rows}


@app.get("/api/leads", tags=["OSINT"], summary="Ostatnie leady (Sesyjnie)")
async def list_leads_session(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 100
) -> dict:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit musi być w zakresie 1–500")
    rows = await get_recent_leads(limit=limit)
    return {"count": len(rows), "leads": rows}


# ---------------------------------------------------------------------------
# API Endpoints - Analytics: Prompt Versions
# ---------------------------------------------------------------------------
@app.get("/api/analytics/prompts", tags=["Analytics"], summary="Historia i KPI wersji promptów")
async def get_prompt_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: int,
    db: AsyncSession = Depends(get_db)
) -> list:
    result = await db.execute(
        select(PromptVersion).filter(PromptVersion.account_id == account_id).order_by(PromptVersion.version.asc())
    )
    versions = result.scalars().all()
    out = []
    for pv in versions:
        lead_result = await db.execute(
            select(
                func.count(Lead.id).label('total'),
                func.sum(case((Lead.status == 'won', 1), else_=0)).label('won'),
                func.sum(case((Lead.status == 'lost', 1), else_=0)).label('lost'),
                func.sum(case((Lead.status == 'in_progress', 1), else_=0)).label('in_progress')
            ).filter(Lead.prompt_version_id == pv.id)
        )
        row = lead_result.one()
        total = row.total or 0
        won = row.won or 0
        lost = row.lost or 0
        in_prog = row.in_progress or 0
        out.append({
            "id": pv.id,
            "version": pv.version,
            "created_at": pv.created_at.isoformat(),
            "prompt_preview": pv.prompt_text[:200] if pv.prompt_text else "",
            "prompt_text": pv.prompt_text,
            "total_leads": total,
            "won_leads": won,
            "lost_leads": lost,
            "in_progress_leads": in_prog,
            "conversion_rate": round(won / total * 100, 1) if total > 0 else 0.0
        })
    return out


@app.post("/api/leads/sync", tags=["OSINT"], summary="Synchronizacja statusów z Odoo")
async def trigger_lead_sync(
    _token: Annotated[str, Depends(verify_token_or_session)]
) -> dict:
    result = await sync_lead_statuses()
    return result


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


@app.post("/api/auth/change-password", tags=["Auth"])
async def change_password(
    req: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Zmienia hasło aktualnie zalogowanego użytkownika."""
    if not verify_password(req.old_password, current_user.salt, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Obecne hasło jest niepoprawne.")
        
    from auth import generate_salt, hash_password
    new_salt = generate_salt()
    current_user.salt = new_salt
    current_user.password_hash = hash_password(req.new_password, new_salt)
    
    await db.commit()
    logger.info("Password changed successfully for user: %s", current_user.username)
    return {"success": True, "message": "Hasło zostało pomyślnie zmienione."}


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
    # Wersjonowanie promptu
    if req.custom_prompt and req.custom_prompt != acc.custom_prompt:
        last_ver_result = await db.execute(
            select(func.max(PromptVersion.version)).filter(PromptVersion.account_id == acc.id)
        )
        last_ver = last_ver_result.scalar() or 0
        new_pv = PromptVersion(
            account_id=acc.id,
            version=last_ver + 1,
            prompt_text=req.custom_prompt,
            created_at=datetime.utcnow()
        )
        db.add(new_pv)
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
    
    if req.value.startswith("...") or "..." in req.value:
        # Maskowana wartość oznacza brak zmian ze strony użytkownika - ignorujemy bez błędu
        return {"success": True}

    item.value = req.value
    await db.commit()
    return {"success": True}


@app.get("/api/settings/default-prompt", tags=["Settings"])
async def get_default_prompt(current_user: Annotated[User, Depends(get_current_user)]):
    """Zwraca obecnie stosowany domyślny prompt systemowy silnika."""
    today_str, start_str = get_date_limits()
    return {"default_prompt": get_system_instruction(today_str, start_str)}


# ---------------------------------------------------------------------------
# API Endpoints - Research Logs (Hard Proof Viewer) & Analytics
# ---------------------------------------------------------------------------
@app.get("/api/analytics/kpis", tags=["Analytics"])
async def get_analytics_kpis(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    # Total scans
    result_total = await db.execute(select(func.count(ResearchLog.id)))
    total_scans = result_total.scalar() or 0
    
    # Success scans
    result_success = await db.execute(select(func.count(ResearchLog.id)).filter(ResearchLog.response_status_code == 200))
    success_scans = result_success.scalar() or 0
    
    failed_scans = total_scans - success_scans
    success_rate = (success_scans / total_scans * 100.0) if total_scans > 0 else 0.0
    
    # Total leads found
    result_found = await db.execute(select(func.sum(ResearchLog.leads_found_count)))
    total_leads_found = result_found.scalar() or 0
    
    # Total leads created
    result_created = await db.execute(select(func.sum(ResearchLog.leads_created_count)))
    total_leads_created = result_created.scalar() or 0
    
    return {
        "total_scans": total_scans,
        "success_rate": round(success_rate, 2),
        "failed_scans": failed_scans,
        "total_leads_found": int(total_leads_found) if total_leads_found else 0,
        "total_leads_created": int(total_leads_created) if total_leads_created else 0
    }


@app.get("/api/analytics/timeline", tags=["Analytics"])
async def get_analytics_timeline(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    stmt = select(
        func.date(ResearchLog.timestamp).label("day"),
        func.count(ResearchLog.id).label("scans"),
        func.sum(ResearchLog.leads_created_count).label("leads_created")
    ).group_by(
        func.date(ResearchLog.timestamp)
    ).order_by(
        func.date(ResearchLog.timestamp).asc()
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    timeline = []
    for row in rows:
        timeline.append({
            "date": row.day,
            "scans": row.scans,
            "leads_created": int(row.leads_created) if row.leads_created is not None else 0
        })
    return timeline


@app.get("/api/logs", tags=["Logs"])
async def get_research_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    result = await db.execute(
        select(ResearchLog, Account)
        .join(Account, Account.id == ResearchLog.account_id)
        .order_by(ResearchLog.timestamp.desc())
        .limit(limit)
    )
    rows = result.all()
    
    resp = []
    for log, acc in rows:
        resp.append({
            "id": log.id,
            "account_id": log.account_id,
            "account_name": acc.name,
            "timestamp": log.timestamp.isoformat(),
            "source": log.source,
            "query_params": json.loads(log.query_params) if log.query_params else {},
            "raw_response_hash": log.raw_response_hash,
            "response_status_code": log.response_status_code,
            "leads_found_count": log.leads_found_count,
            "leads_created_count": log.leads_created_count,
            "log_text": log.log_text,
            "odoo_company_id": acc.odoo_company_id,
            "odoo_user_id": acc.odoo_user_id,
            "odoo_tag_ids": json.loads(acc.odoo_tag_ids) if acc.odoo_tag_ids else [],
            "odoo_team_id": acc.odoo_team_id,
            "odoo_source_id": acc.odoo_source_id
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
    from google import genai
    from google.genai import types
    
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

# Rejestracja ze statycznymi zasobami
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
