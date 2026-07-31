# PLAN-041: DOMSanitizer BeautifulSoup HTML Tag Decomposition & Cookie Consent Removal

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Fix cookie banner text leakages in Piaskownica AI and scraper pipelines by integrating BeautifulSoup HTML tag decomposition directly inside `DOMSanitizer.clean`.

---

## 🔍 Root Cause Analysis
1. Trafilatura alone does not filter out Vue.js/React modal components (e.g. `<div class="cookie-manager">`) embedded in modern Web App DOMs like `platformazakupowa.pl`.
2. As a result, cookie consent modal text leaked into `clean_text` in Piaskownica AI ("We use solutions from our partners: Google and Meta...").
3. By decomposing HTML elements with `class`, `id`, or `test-id` matching `cookie`, `consent`, `rodo`, `privacy`, `modal`, or `banner` BEFORE running `trafilatura.extract`, the cookie modal DOM trees are physically eliminated from the document prior to text extraction.
4. Input text size drops from ~8,000 chars to ~1,500 chars, preserving 100% of procurement titles, IDs, dates, investors, and specs.

---

## 🏗️ Implementation Details
1. **`DOMSanitizer.clean` Pre-cleaning (`src/scrapers/base.py`)**:
   - Parse `html_content` with `BeautifulSoup(html_content, "html.parser")`.
   - Decompose elements matching `class`, `id`, or `test-id` containing `cookie`, `consent`, `rodo`, `privacy`, `modal`, `banner`, or `wadium`.
   - Pass pre-cleaned HTML string to `trafilatura.extract(...)`.
   - Post-process remaining boilerplate strings.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.41).
- **Builder (Subagent)**: Implement BS4 tag decomposition in `src/scrapers/base.py`, update unit tests, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit BS4 tag decomposition and content preservation, verify math/logic, and generate auditor handshake.
