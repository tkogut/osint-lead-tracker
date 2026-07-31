# PLAN-039: PlatformaZakupowa.pl Scraper Plugin (Phase 1: Public Scraping)

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Implement a dedicated scraper plugin `PlatformaZakupowaScraper` for `https://platformazakupowa.pl` (Open Nexus) in Phase 1 (public notices scraping without login), allowing automatic extraction of transactions into Odoo and Piaskownica testing.

---

## 🔍 Architecture & Features
1. **Public Listing Crawling (`src/scrapers/platforma_zakupowa.py`)**:
   - `PlatformaZakupowaScraper` inherits from `BaseScraper`.
   - Uses `AsyncSession(impersonate="chrome124")`.
   - First visits `https://platformazakupowa.pl/all` to establish session cookies.
   - Crawls paginated listings (`https://platformazakupowa.pl/all?page={page}&limit=30`).
   - Extracts all `/transakcja/<id>` links.
2. **Tier 0 Deduplication & Keyword Matching**:
   - Deduplicates unvisited transaction URLs via `is_url_visited(detail_url, account.id)`.
   - Sanitizes detail HTML via `DOMSanitizer.clean`.
   - Filters notice text using Polish keyword inflection matcher (`match_polish_keywords`).
3. **Factory & UI Registration**:
   - Registered in `src/scrapers/factory.py` under `"PlatformaZakupowa"`.
   - Added to `AVAILABLE_SOURCES` in `src/main.py`.
   - Added to Piaskownica AI source dropdowns in `src/main.py` and `src/static/index.html`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.39).
- **Builder (Subagent)**: Implement `PlatformaZakupowaScraper` in `src/scrapers/platforma_zakupowa.py`, register in factory and UI, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit scraper implementation, session cookie handling, and syntax verification, then generate auditor handshake.
