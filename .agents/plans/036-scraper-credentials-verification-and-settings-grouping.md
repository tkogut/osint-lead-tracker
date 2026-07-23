# PLAN-036: Scraper Credentials Verification and Settings Grouping

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
1. Restructure the Settings dashboard panel by grouping settings into clear, styled category cards.
2. Implement backend credentials verification for Automatyka (Xtech.pl) and Logintrade (platformazakupowa.logintrade.pl).
3. Add a "Test Connection" button next to each scraper in the Settings tab UI.

---

## 🏗️ Implementation Details

### 1. Schemas (`src/schemas.py`)
- Define `VerifyCredentialsRequest` model containing:
  - `scraper`: str
  - `username`: str
  - `password`: str

### 2. Backend Endpoint (`src/main.py`)
- Implement `POST /api/settings/verify-credentials`.
- Retrieve stored username/password from database if parameters are masked (`******`) or empty.
- For `Automatyka`: Make POST to `https://www.xtech.pl/zaloguj` and check JSON `errorId`.
- For `Logintrade`: Fetch `https://platformazakupowa.logintrade.pl/sso-login`, parse CSRF token, POST to `/sso-login`, check if HTML contains `invalid` wrapper.

### 3. Frontend Restructuring (`src/static/index.html` & `src/static/app.js`)
- Replace the static Settings inputs and `#settings-fields-container` in `index.html` with a clean `#settings-sections-container` loaded dynamically.
- Modify `app.js` to render settings by groups (AI, Odoo, Scheduler, Security, Scrapers).
- Add click event delegates for `.btn-test-auth` in `app.js` to trigger verification and show toasts.

---

## 🛠️ Roles
- **Coordinator**: Create plan, validate handshakes, execute commit.
- **Builder (Subagent)**: Implement code changes in `schemas.py`, `main.py`, `index.html`, `app.js`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit changes, verify login logic for both platforms, check for credential leakage, and generate auditor handshake.
