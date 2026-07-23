# PLAN-032: Modular Scraper Credentials & Authenticated Scraping System

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Implement a modular, expandable Scraper Authentication System allowing users to configure login credentials (login/password) for dedicated scrapers in the **Settings** panel.
- Phase 1: **Automatyka.pl / Xtech network** (`https://www.xtech.pl/zaloguj`).
- Future-proof structure for **Logintrade** and other scrapers.
- Scrapers with credentials will log in, acquire session cookies, and extract full advertiser contact details (Company name, Contact person, Email, Phone, Full address).

---

## 🏗️ Implementation Details

### 1. Database Settings & API (`src/seed.py`, `src/main.py`)
- Register global setting keys:
  - `SCRAPER_AUTOMATYKA_USER`, `SCRAPER_AUTOMATYKA_PASS`
  - `SCRAPER_LOGINTRADE_USER`, `SCRAPER_LOGINTRADE_PASS`
- Expose settings update in `/api/settings` and `/api/settings/get` (masking passwords as `******` for security).

### 2. Settings UI (`src/static/index.html`, `src/static/app.js`)
- Add a new card section in Settings tab:
  **🔐 Dostęp i Logowanie do Scraperów (Dedykowane Źródła)**
- Provide input fields for Automatyka.pl (Login, Password) and Logintrade (Login, Password).
- Bind UI inputs to load and save via settings API.

### 3. Authenticated Scraper (`src/scrapers/automatyka.py`)
- In `AutomatykaScraper.fetch_leads`:
  - Check for `SCRAPER_AUTOMATYKA_USER` & `SCRAPER_AUTOMATYKA_PASS`.
  - Perform POST login to `https://www.xtech.pl/zaloguj` (`LoginName`, `Password`, `ServiceId=3`, `Step=1`) via `curl_cffi` AsyncSession.
  - When authenticated, parse detail pages for **Dane ogłaszającego**:
    - Nazwa firmy
    - Osoba kontaktowa
    - Adres e-mail
    - Nr telefonu
    - Adres do kontaktu
  - Include contact header in `raw_text` passed to LLM.

### 4. Sandbox Fetch URL Support (`src/main.py`)
- Update `/api/sandbox/fetch-url` to perform authenticated fetch for `automatyka.pl` URLs if credentials are configured.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.10).
- **Builder (Subagent)**: Implement backend settings, UI inputs, authenticated scraper logic in `automatyka.py`, sandbox fetch support, verify syntax, and generate builder handshake.
