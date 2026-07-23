# PLAN-037: Sandbox Scraper Context & Logintrade Auth in Daily Skan

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
1. Implement scraper-specific credentials authentication for Logintrade during daily scans (pipeline).
2. Integrate Scraper Context dropdown into Sandbox UI so that users can test scraping of login-restricted URLs.
3. Align sandbox URL fetching to reuse the exact login flow as daily scrapers.

---

## 🏗️ Implementation Details

### 1. Daily Scraper Login (`src/scrapers/logintrade.py`)
- In `fetch_leads()`, load `SCRAPER_LOGINTRADE_USER` and `SCRAPER_LOGINTRADE_PASS` from database settings using `get_db_setting_sync`.
- If credentials are present, execute login flow (GET `sso-login` page, parse `_token`, and POST credentials to `sso-login?backUrl=...`) using the current session before beginning notice listing pagination.

### 2. Schemas (`src/schemas.py`)
- Update `SandboxFetchUrlRequest` model:
  - Add `scraper: Optional[str] = "Auto"`

### 3. Backend Sandbox Fetch (`src/main.py`)
- In `sandbox_fetch_url()` endpoint:
  - Resolve context: if `req.scraper == "Auto"`, detect from domain in `req.url` (e.g. `"automatyka.pl"` / `"xtech.pl"` -> Automatyka, `"logintrade.pl"` / `"logintrade.net"` -> Logintrade).
  - If context is `Automatyka`: Run Automatyka login (xtech) in session, then fetch `req.url`.
  - If context is `Logintrade`: Run Logintrade login in session (get page, parse `_token`, post credentials), then fetch `req.url`.
  - Clean text and return it.

### 4. Sandbox UI (`src/static/index.html` & `src/static/app.js`)
- Add dropdown `#sandbox-scraper-context` near the URL input in `index.html`.
- Read and send chosen context in `app.js` when triggering `fetch-url` from the Sandbox.

---

## 🛠️ Roles
- **Coordinator**: Create plan, validate handshakes, execute commit.
- **Builder (Subagent)**: Implement backend login in Logintrade, update endpoint, add select box to UI, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit Logintrade daily auth flow, check sandbox fetch logic, and generate auditor handshake.
