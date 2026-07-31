# PLAN-045: Logs Pagination (50/page), Updated Source Filters, Timeline & Recent Opportunities Windows (10)

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
1. Implement server & client-side pagination for Research Logs (`50` items per page with Prev/Next navigation and page counters).
2. Limit Dashboard Recent Acquired Opportunities to `10` items.
3. Limit Dashboard Activity Timeline to `10` most recent window entries.
4. Update Log Filter sources dropdown with all current scrapers (`PlatformaZakupowa`, `Logintrade`, `Automatyka`, `BiznesPolska`, `BazaKonkurenconosci`, `Ezamowienia`, `BZP`, `Google`, `GUNB`, `Manual`).

---

## 🔍 Implementation Details
1. **Backend (`src/main.py`)**:
   - `GET /api/logs`: Add pagination params (`page=1`, `limit=50`, `source`, `account_id`, `status`, `search`, `date_start`, `date_end`). Return `{"items": [...], "total": int, "page": int, "limit": int, "pages": int}`.
   - `GET /api/analytics/timeline`: Support `limit: int = 10` (default 10 most recent activity days).
   - `GET /api/leads`: Set default `limit: int = 10` for Dashboard recent leads.
2. **Frontend UI (`src/static/index.html`)**:
   - Update `#log-filter-source` dropdown options with all registered sources.
   - Add pagination control bar (`#logs-pagination`) below `#logs-table-body` with Previous/Next buttons and page indicator `Strona X z Y (Łącznie Z logów)`.
3. **Frontend JS (`src/static/app.js`)**:
   - Update `loadLogsData()` to handle 50 logs/page pagination.
   - Update Dashboard `loadLeadsData()` to fetch 10 recent opportunities (`/api/leads?limit=10`).
   - Wire Prev/Next page handlers and page size (50) rendering.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.45).
- **Builder (Subagent)**: Implement pagination and UI window updates across `src/main.py`, `src/static/index.html`, `src/static/app.js`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit pagination math, window constraints (10 items), source filter accuracy, and generate auditor handshake.
