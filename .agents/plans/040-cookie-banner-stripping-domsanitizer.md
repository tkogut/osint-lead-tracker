# PLAN-040: DOMSanitizer Cookie & GDPR Consent Banner Stripping

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Strip cookie consent notices, GDPR marketing policy text (Google Analytics, Meta Pixel, Clarity, LinkedIn Tag), and platform ad noise from raw extracted HTML in `DOMSanitizer` to save LLM tokens and eliminate AI hallucinations.

---

## 🔍 Root Cause Analysis
1. Raw HTML extracted from `platformazakupowa.pl` and other portals includes large cookie consent footers (~4,500 characters of cookie/GDPR noise).
2. Passing this boilerplate noise into `raw_text` wastes over 1,000 tokens per prompt request and causes potential LLM confusion.
3. Filtering out cookie/GDPR boilerplate text is 100% safe as it removes zero procurement content (preserving Proceeding ID, title, dates, investor, scope, and specs).

---

## 🏗️ Implementation Details
1. **`DOMSanitizer` Boilerplate Regex Patterns (`src/scrapers/base.py`)**:
   - Add patterns for OpenNexus / PlatformaZakupowa cookie & privacy policy banners (English & Polish).
   - Add patterns for platform ad widgets ("Wadium w 2 minuty", "Bid bond in 2 minutes").
2. **Apply in Piaskownica AI & Scraper Pipelines**:
   - Ensure `DOMSanitizer.clean` strips boilerplate text automatically across all scraper plugins and Piaskownica URL fetches.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.40).
- **Builder (Subagent)**: Implement cookie consent stripping in `src/scrapers/base.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit sanitization safety & content preservation, verify math/logic, and generate auditor handshake.
