# PLAN-038: Fix Generic URL Collision in Lead Deduplication

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Fix the bug where different leads scraped from generic platform URLs (e.g. `https://platformazakupowa.pl` or parent listing pages) are falsely flagged as "duplicates" and skipped from being sent to Odoo.

---

## 🔍 Root Cause Analysis
1. Previously, `url_exists(url)` checked only `Lead.url == url`.
2. When multiple different inquiries were scraped from a generic procurement platform or parent list page that shared the same base URL (e.g., `https://platformazakupowa.pl/` or `https://ezamowienia.gov.pl`), the first lead was saved with that URL.
3. Subsequent DIFFERENT leads (such as `Usługa wzorcowania wyposażenia pomiarowo-badawczego, ZP-DL-53/26`) sharing that generic URL were falsely identified as "duplicate URL" and skipped before calling `odoo.create_lead`.
4. As a result, Odoo never received the lead even though it was a brand-new inquiry.

---

## 🏗️ Implementation Details

### 1. Robust Lead Deduplication (`src/database.py`)
- Implement `lead_exists(url: str, title: str = "", account_id: Optional[int] = None) -> bool`:
  - Check if a lead with exact matching `url` AND matching `tytul` / `nazwa_inwestycji` exists for the account.
  - If `url` is generic (e.g. root domain or listing page), require matching title/content before declaring duplicate.
  - If URL contains notice ID/UUID or title is unique, allow creation.

### 2. Pipeline Deduplication Update (`src/main.py`)
- Replace simple `await url_exists(url)` with `await lead_exists(url, title=title, account_id=account.id)` in `trigger_osint_pipeline`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.38).
- **Builder (Subagent)**: Implement `lead_exists` in `src/database.py` and update pipeline deduplication in `src/main.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit deduplication logic and generic URL collision safety, verify math/logic, and generate auditor handshake.
