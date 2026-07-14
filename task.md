# Backlog: Lead Dashboard Module (AGENTS-OS v5.0)

## [Phase 1: Database & Multi-tenancy Core]
- [x] **TSK-001**: Implement SQLAlchemy models in `src/models.py` supporting Account, ResearchLog, User, Session, Setting.
- [x] **TSK-002**: Refactor `src/database.py` to support both asynchronous operations (for FastAPI) and synchronous SQLAlchemy sessions for background tasks.
- [x] **TSK-003**: Create database migration/initialization script to seed the initial default account and admin user if empty.

## [Phase 2: Engine Parameterization & Scheduler]
- [ ] **TSK-004**: Refactor `src/osint_engine.py` to accept an `Account` configuration dynamically instead of reading global `Settings` from `.env`.
- [ ] **TSK-005**: Modify `run_osint_pipeline` in `src/main.py` to iterate over all active accounts, run research per account, and log lightweight "Hard Proofs" in `ResearchLog`.
- [ ] **TSK-011**: Update Odoo integration client in `src/odoo_integration.py` to accept `company_id`, `user_id` (salesperson), and `tag_ids` dynamically per lead insertion.

## [Phase 3: Backend API & Authentication]
- [x] **TSK-006**: Implement secure session-based authentication (login, logout, active sessions) in `src/main.py`.
- [x] **TSK-007**: Implement CRUD endpoints for `Account` management (restricted to admin users).
- [x] **TSK-008**: Implement REST API endpoint for the LLM Sandbox (`POST /api/sandbox/test`) which takes a custom prompt, temperature, and raw notice text, runs Gemini, and returns the parsed result.
- [x] **TSK-009**: Implement API endpoint to retrieve `ResearchLog` entries with filtering by account and status.

## [Phase 4: Frontend UI (Lead Dashboard)]
- [x] **TSK-010**: Create modern, responsive HTML/CSS/JS frontend in `src/static/` with a premium dark-mode dashboard (Deep Blue palette, glassmorphism, Outfit font) containing Dashboard, Accounts, Sandbox, Logs and Settings tabs.
