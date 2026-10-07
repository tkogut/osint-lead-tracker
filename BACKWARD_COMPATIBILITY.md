# Protected Contract Surfaces & Backward Compatibility

This document inventories the public and internal contract surfaces protected against breaking changes in `osint-lead-tracker`.

---

## 1. Protected Surfaces

### A. REST API Endpoints
- **Liveness & Health (`GET /health`)**:
  - Response contract: `status`, `system_status`, `service`, `version`, `scheduler`, `sanitizer`.
- **Leads API (`GET /api/leads`, `POST /api/leads/{id}/sync-odoo`, `POST /api/leads/{id}/reject`)**:
  - Pagination contract: `items`, `total`, `page`, `limit`, `pages`.
  - Item fields: `id`, `url`, `tytul`, `inwestor`, `zakres`, `uzasadnienie`, `status`, `odoo_id`, `created_at`.
- **Accounts & Campaigns (`GET /api/accounts`, `POST /api/accounts`, `PUT /api/accounts/{id}`)**:
  - Structure must maintain backwards compatibility with existing multi-tenancy configurations.
- **Analytics & Timeline (`GET /api/analytics/timeline`)**:
  - Query parameter `range_type` (`1d`, `7d`, `1m`, `3m`, `6m`, `1y`, `5y`, `all`).
  - Response: list of `{"date": str, "scans": int, "leads_created": int}`.

### B. SQLite Database Schema (`src/models.py`)
- Tables: `leads`, `accounts`, `research_logs`, `settings`, `prompt_versions`, `run_performance_snapshots`, `visited_urls`, `users`, `sessions`.
- **Migration Policy**:
  - Column additions must be idempotent (`ALTER TABLE ... ADD COLUMN ...` with try/except in `database.init_db`).
  - Existing column names and types MUST NOT be renamed or deleted without backwards-compatible data migration.

### C. Odoo CRM XML-RPC Integration
- Target model: `crm.lead`.
- Field mappings: `name` (lead title), `description` (scope + rationale + url), `partner_id` / contact details, `team_id`, `tag_ids`, `company_id`.
- Sync failures must never block pipeline completion or discard newly found leads in SQLite.

### D. Scraper Plugin Interface (`src/scrapers/base.py`)
- `BaseScraper` contract: `fetch_leads(account, start_date, today_date) -> list[dict]`.
- Output dictionaries must include at least: `url` and `raw_text` (or structured tender fields).

---

## 2. Breaking Changes & Deprecation Rules

1. **API Changes**:
   - Dropping or renaming existing response fields requires a deprecation window or a version bump.
   - Adding optional fields is backwards-compatible and permitted.
2. **Database Migrations**:
   - Always run non-destructive, idempotent column additions during startup (`database.init_db`).
3. **Environment Settings**:
   - New environment variables in `src/config.py` MUST provide sensible defaults unless they are mandatory third-party credentials.
