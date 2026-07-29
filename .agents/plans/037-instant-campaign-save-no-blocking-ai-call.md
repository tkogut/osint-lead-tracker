# PLAN-037: Instant Campaign Save & Elimination of Blocking AI Calls in Account Endpoints

**Status:** IN_PROGRESS  
**Date:** 2026-07-29  

---

## 🎯 Goal
Eliminate the campaign save freeze, container restart, and login window redirect by removing blocking AI calls and synchronous DB session locks from `POST /api/accounts` and `PUT /api/accounts/{id}`. Campaign save will execute instantly (under 20ms).

---

## 🔍 Root Cause Analysis
1. `POST /api/accounts` and `PUT /api/accounts/{id}` called `await expand_keywords_via_ai(req.target_keywords)`.
2. `expand_keywords_via_ai` opened a synchronous `SessionLocal()` DB query on `sync_engine` while `AsyncSession` was active on the HTTP request thread, creating SQLite DB file lock deadlocks.
3. `expand_keywords_via_ai` made external network requests to Google Gemini API during the HTTP request lifecycle. When network latency occurred, the HTTP request hung for >15s, triggering Docker healthcheck container restarts and logging out the user.
4. Dynamic Polish keyword stemming (`match_polish_keywords` in `src/utils.py`) already handles Polish keyword inflections natively during scraping, rendering blocking AI expansion during HTTP save unnecessary.

---

## 🏗️ Implementation Details
1. **Instant Account Save (`src/main.py`)**:
   - In `create_account` and `update_account`, save `req.target_keywords` directly into `target_keywords` without waiting for external AI network calls.
   - Clean up `expand_keywords_via_ai` or move optional expansion to an explicit async background task.
2. **Eliminate DB Lock Conflict**:
   - Avoid calling `get_db_setting_sync` inside HTTP request handlers.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.37).
- **Builder (Subagent)**: Implement instant account save in `src/main.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit campaign save performance & non-blocking execution, verify math/logic, and generate auditor handshake.
