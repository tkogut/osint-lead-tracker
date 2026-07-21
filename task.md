# Backlog: Lead Dashboard Module (AGENTS-OS v5.0)
**Ostatnia synchronizacja:** 2026-07-15T14:15:00+02:00 | **Gałąź:** `main` | **Commit:** `211c964`

---

## [Phase 1: Database & Multi-tenancy Core] ✅ DONE
- [x] **TSK-001**: Implement SQLAlchemy models in `src/models.py` supporting Account, ResearchLog, User, Session, Setting.
- [x] **TSK-002**: Refactor `src/database.py` to support both asynchronous operations (for FastAPI) and synchronous SQLAlchemy sessions for background tasks.
- [x] **TSK-003**: Create database migration/initialization script to seed the initial default account and admin user if empty.

## [Phase 2: Engine Parameterization & Scheduler] ✅ DONE
- [x] **TSK-004**: Refactor `src/osint_engine.py` to accept an `Account` configuration dynamically instead of reading global `Settings` from `.env`.
- [x] **TSK-005**: Modify `run_osint_pipeline` in `src/main.py` to iterate over all active accounts, run research per account, and log lightweight "Hard Proofs" in `ResearchLog`.
- [x] **TSK-011**: Update Odoo integration client in `src/odoo_integration.py` to accept `company_id`, `user_id` (salesperson), and `tag_ids` dynamically per lead insertion.

## [Phase 3: Backend API & Authentication] ✅ DONE
- [x] **TSK-006**: Implement secure session-based authentication (login, logout, active sessions) in `src/main.py`.
- [x] **TSK-007**: Implement CRUD endpoints for `Account` management (restricted to admin users).
- [x] **TSK-008**: Implement REST API endpoint for the LLM Sandbox (`POST /api/sandbox/test`) which takes a custom prompt, temperature, and raw notice text, runs Gemini, and returns the parsed result.
- [x] **TSK-009**: Implement API endpoint to retrieve `ResearchLog` entries with filtering by account and status.

## [Phase 3 Expansion: Analytics & Monitoring] ✅ DONE
- [x] **TSK-012**: Implement backend API endpoints for analytics (`GET /api/analytics/kpis` and `GET /api/analytics/timeline`).
- [x] **TSK-013**: Implement advanced UI search, filtering and detail modal/accordion for `ResearchLog` (Twarde Dowody).
- [x] **TSK-014**: Implement UI Notification Gate showing alerts for API failure status codes (4xx/5xx).
- [x] **TSK-015**: Visualize Odoo Multicompany mapping fields (`company_id`, `user_id`, `tag_ids`) in Accounts and Logs tabs.
- [x] **TSK-016**: Restructure Campaign Edit modal layout to two-column format (left settings, right prompt).

## [Phase 4: Frontend UI (Lead Dashboard)] ✅ DONE
- [x] **TSK-010**: Create modern, responsive HTML/CSS/JS frontend in `src/static/` with a premium dark-mode dashboard (Deep Blue palette, glassmorphism, Outfit font) containing Dashboard, Accounts, Sandbox, Logs and Settings tabs.

## [Phase 5: Prompt Versioning & CRM Feedback Loop] ✅ DONE — 2026-07-15
- [x] **TSK-017**: Create the `PromptVersion` database model and update the `Lead` model with `status`, `prompt_version_id`, `last_synced_at` columns. Idempotentna migracja ALTER TABLE w `init_db()`. — `src/models.py`, `src/database.py`
- [x] **TSK-018**: Implement backend feedback sync background task `POST /api/leads/sync` querying Odoo lead states (`probability`, `active`). Scheduler cron 07:00 daily (`odoo_sync`). Method `get_lead_status()` w OdooClient. — `src/main.py`, `src/odoo_integration.py`
- [x] **TSK-019**: Implement backend prompt versioning (auto-create on `custom_prompt` change) and performance ranking API `GET /api/analytics/prompts?account_id=<ID>`. Zwraca: `version`, `created_at`, `total_leads`, `won_leads`, `lost_leads`, `conversion_rate`. Bug fix: `case()` zamiast `func.cast()` dla SQLite. — `src/main.py`
- [x] **TSK-020**: Design and implement the prompt history panel (`#prompt-version-section`) and version list in the Campaign Edit modal UI. Function `loadPromptVersionHistory(accountId)` w JS. — `src/static/index.html`, `src/static/app.js`

**Swarm Triad (Phase 5 Core):**
- Builder `ecf5ed62` → `ecf5ed62_builder_handshake.json` ✅ SUCCESS
- Auditor `75929465` → `75929465_auditor_handshake.json` ⚠️ 2 CRITICAL BUGS wykryte i naprawione przez Coordinator
- Commit: `b1b6ff1` → VPS deployed ✅

## [Phase 5 Expansion: Revert Prompt & Lead Filtering] ✅ DONE — 2026-07-15
- [x] **TSK-021**: Przycisk "Przywróć tę wersję" — nadpisuje prompt wybraną wersją historyczną z bazy i odświeża UI. Zabezpieczono przed błędami parsowania cudzysłowów w JS. — `src/static/app.js`, `src/main.py` (dodano `prompt_text` do API).
- [x] **TSK-022**: Widok leadów z filtrem po statusie (`new`/`in_progress`/`won`/`lost`) i sortowaniem (najnowsze, najstarsze, priorytet). Dodano kolumnę "Status" z dopasowanymi kolorystycznie badge'ami do tabeli leadów. — `src/static/index.html`, `src/static/app.js`, `src/database.py` (fix: dodanie `status` do API).

**Swarm Triad (TSK-021/022):**
- Builder `906072fc` → `906072fc-7778-498e-9e05-70e8194b44b8_builder_handshake.json` ✅ SUCCESS
- Auditor `05942848` → `05942848-ba6f-4d2a-8d4f-e6eb084666d4_auditor_handshake.json` ⚠️ 1 BUG (brak statusu w database.py) wykryty i naprawiony przez Coordinator
- Commit: `211c964` → VPS deployed ✅

**Swarm Triad (Custom Campaigns Fix):**
- Builder `d42568ec` → `d42568ec-abf2-4796-8fdf-b21a0d1e9b55_builder_handshake.json` ✅ SUCCESS
- Auditor `bd7463c5` → `bd7463c5-3383-4d3e-8db2-7489f3da3884_auditor_handshake.json` ✅ SUCCESS
- Commit: `d74f53b` → VPS deployed ✅

**Swarm Triad (Scan Specific Campaign):**
- Builder `7f4eb6cb` → `7f4eb6cb-9643-450c-b41e-13a57e3e289d_builder_handshake.json` ✅ SUCCESS
- Auditor `e73a5ae7` → `e73a5ae7-38a8-4b19-a2d3-b3b501935e4b_auditor_handshake.json` ✅ SUCCESS
- Commit: `55596f6` → VPS deployed ✅

## [Phase 6: Analytics Architecture & Performance Upgrades] ✅ DONE — 2026-07-16
- [x] **TSK-025**: Implementacja nowej bazy metryk (Yield, Yield/Chunk, Queries) opartej o dynamiczne dane z `grounding_metadata` Gemini, eliminując "próżne wskaźniki".
- [x] **TSK-026**: Integracja systemu buforowania i zabezpieczeń **Circuit Breaker** (`MAX_LEADS_PER_RUN`) zapobiegającego zatruciu Odoo CRM spamem lub halucynacjami Gemini. Leady trafiają do kwarantanny (`pending_approval`) na dashboardzie.
- [x] **TSK-027**: Dodanie asynchronicznej kolejki `asyncio.Queue` z dedykowanym workerem (Single Writer) do zapisu snapshotów w bazie SQLite, całkowicie eliminując błędy `database is locked`.
- [x] **TSK-028**: Zastąpienie sztywnego opisu "Budowa wagi samochodowej" w pozwolenize budowlanych GUNB dynamiczną nazwą kampanii (Account Name).
- [x] **TSK-029**: Wdrożenie w panelu UI sekcji Kwarantanny z listą oczekujących leadów, podglądem i manualną akceptacją do Odoo (z poprawnym dziedziczeniem mapowań firmy/handlowca i obsługa błędów transakcji).

**Swarm Triad (Analytics & Performance Upgrade):**
- Builder `1e23a48f` → `1e23a48f-a938-404c-bfe7-ec2774e0103f_builder_handshake.json` ✅ SUCCESS
- Auditor `49d69000` → `49d69000-026d-41a8-8592-bd84e1567d76_auditor_handshake.json` ✅ SUCCESS
- Commit: `24f71ab` → VPS deployed ✅

**Swarm Triad (Dynamic GUNB Title):**
- Builder `8725d757` → `8725d757-71bb-4108-8894-097ce6288579_builder_handshake.json` ✅ SUCCESS
- Auditor `7c508b9f` → `7c508b9f-cee2-48f2-bc6d-e4a1fa9ad717_auditor_handshake.json` ✅ SUCCESS
- Commit: `211c6c7` → VPS deployed ✅

---

## [Phase 7: Konfigurowalne Źródła Wyszukiwania w Kampaniach] ✅ DONE — 2026-07-21
- [x] **TSK-030 (PLAN-016)**: Wybór aktywnych źródeł wyszukiwania (checkboxy: BZP, Google, GUNB) per kampania z walidacją "Zero-Source" w API oraz dynamicznym wykluczaniem z logów analitycznych.

**Swarm Triad (Campaign Search Sources):**
- Builder `db4ec13c` → `db4ec13c-820d-4e86-ab2d-cd58d2370194_builder_handshake.json` ✅ SUCCESS
- Auditor `db4ec13c` → `db4ec13c-820d-4e86-ab2d-cd58d2370194_auditor_handshake.json` ✅ SUCCESS
- Commit: `6dd39da` → Remote pushed ✅

---

## [Phase 8: Hybrydowa Architektura OSINT & Modularne Wtyczki] ✅ DONE — 2026-07-21
- [x] **TSK-031 (PLAN-017)**: Tabela `visited_urls` w SQLite & deduplikacja Tier 0 (Pre-LLM) zapobiegająca zbędnym wywołaniom HTTP/Gemini.
- [x] **TSK-032 (PLAN-017)**: Abstrakcyjna klasa bazowa `BaseScraper`, czyszczenie DOM `DOMSanitizer` (Trafilatura) oraz wtyczka `AutomatykaScraper` (`curl_cffi` impersonate Chrome).
- [x] **TSK-033 (PLAN-017)**: Wzorzec Strategii i Fabryki w `OSINTEngine` z bezwzględnym zachowaniem 100% kompatybilności dla BZP, GUNB i Google Search Grounding.

**Swarm Triad (Hybrid OSINT Engine & Scraper Plugins):**
- Builder `53ae3993` → `53ae3993-52e8-4266-9345-bc12cc87aba5_builder_handshake.json` ✅ SUCCESS
- Auditor `53ae3993` → `53ae3993-52e8-4266-9345-bc12cc87aba5_auditor_handshake.json` ✅ SUCCESS



