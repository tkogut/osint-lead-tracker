# PLAN-046: Modern Scalable Dashboard Redesign (Interactive Scans vs Leads Chart 1D-5Y, Recent Opportunities Pagination 10/page & Campaign Filter Fix)

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
1. **Interactive Scalable Analytics Chart**: Replace static timeline with a high-performance interactive trend chart (Scans vs Leads Created) with time range selector buttons (`1D`, `7D`, `1M`, `3M`, `6M`, `1Y`, `5Y`, `ALL`).
2. **Dashboard Recent Opportunities Pagination**: Add server & client-side pagination (`10` items per page with Prev/Next buttons) to browse historical leads easily.
3. **Campaign Filter Update in Logs**: Ensure `#log-filter-campaign` accurately syncs with all active/archived campaigns and filters logs dynamically.

---

## 🏗️ Implementation Details

### 1. Backend (`src/main.py`)
- **`GET /api/analytics/timeline`**:
  - Accept `range_type: str = "7d"` (`1d`, `7d`, `1m`, `3m`, `6m`, `1y`, `5y`, `all`).
  - Calculate cutoff date based on `range_type`.
  - Group by date (or hour for `1d`), returning array of `{"date": str, "scans": int, "leads_created": int}`.
- **`GET /api/leads`**:
  - Accept `page: int = 1`, `limit: int = 10`, `account_id: Optional[int] = None`.
  - Return `{"items": [...], "total": int, "page": int, "limit": int, "pages": int}`.

### 2. Frontend Layout & CSS (`src/static/index.html`)
- Replace bulky timeline text with a **Sleek Interactive Canvas/SVG Chart Container** in `#tab-dashboard`.
- Render range selector pill buttons (`1D`, `7D`, `1M`, `3M`, `6M`, `1Y`, `5Y`, `Wszystkie`).
- Add pagination controls (`#leads-pagination`) below Recent Opportunities table with `Strona X z Y (Łącznie Z szans)` and Prev/Next buttons.

### 3. Frontend Logic (`src/static/app.js`)
- Implement SVG / Canvas chart renderer with interactive hover tooltips (Scans vs Leads Created).
- Connect range button clicks to fetch `/api/analytics/timeline?range_type=X` and re-render chart dynamically.
- Connect `#leads-pagination` Prev/Next buttons to fetch `/api/leads?page=X&limit=10`.
- Verify campaign filter (`#log-filter-campaign`) dropdown population and instant filtering.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.46).
- **Builder (Subagent)**: Implement backend timeline ranges, leads pagination endpoint, frontend SVG chart renderer, and campaign filter updates.
- **Auditor (Subagent)**: Audit chart data calculations, range cutoff dates, pagination math, and generate auditor handshake.
