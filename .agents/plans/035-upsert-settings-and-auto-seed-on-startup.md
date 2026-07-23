# PLAN-035: Fix Settings Upsert & Automatic Startup Seeding

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Fix the `"Ustawienie nie istnieje"` 404 error when saving new scraper credentials or settings on existing database installations.

---

## 🏗️ Implementation Details

### 1. Settings Endpoint Upsert (`src/main.py`)
- Update `PUT /api/settings`:
  If a setting key does not exist in `settings` table, upsert it (add `Setting(key=req.key, value=req.value)`) instead of throwing a 404 error.
- Update `GET /api/settings`:
  Ensure all declared setting keys (including `SCRAPER_AUTOMATYKA_USER`, `SCRAPER_AUTOMATYKA_PASS`, `SCRAPER_LOGINTRADE_USER`, `SCRAPER_LOGINTRADE_PASS`) are always returned in the list (with default empty string if missing in DB).

### 2. Automatic Seeding on Startup (`src/main.py`)
- Import `seed_data` from `seed.py` into `main.py`.
- Call `await seed_data()` inside `lifespan` startup event so new database keys are automatically synchronized into existing databases upon container restart.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.13).
- **Builder (Subagent)**: Implement upsert in `main.py`, update `lifespan`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Conduct QA audit of settings API fix, verify math/logic, and generate auditor handshake.
