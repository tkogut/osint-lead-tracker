# PLAN-048: Smart Title Normalization & Cross-Source Lead Deduplication

**Status:** IN_PROGRESS  
**Date:** 2026-09-04  

---

## 🎯 Goal
Eliminate duplicate lead creation across different sources (e.g. BZP direct API vs Google Search Grounding aggregators) by introducing robust title normalization (`normalize_title`) and token-set similarity matching (>=85% word overlap) inside `lead_exists`.

---

## 🔍 Root Cause Analysis
1. Exact string comparison `Lead.tytul == title_clean` failed when titles had quote discrepancies (e.g. `„Kompleksowa modernizacja...”` vs `Kompleksowa modernizacja...”`), different dash types (`–` vs `-`), or minor punctuation variations.
2. Official BZP notices and Google Search Grounding aggregator URLs (e.g. `tendario.pl`, `egospodarka.pl`, `biznesoferty.pl`) had different URLs for the exact same tender, making URL-only deduplication insufficient.

---

## 🏗️ Implementation Details
1. **Title Normalization & Token Set Similarity (`src/database.py`)**:
   - Implement `normalize_title(title: str) -> str`: Strips typographic quotes (`„`, `”`, `"`, `'`, `«`, `»`, `’`, `‘`, `‚`, `“`), standardizes dashes/hyphens, lowercases, removes non-alphanumeric noise, and collapses whitespace.
   - Implement `is_title_duplicate(title1: str, title2: str) -> bool`: Checks exact normalized equality and token set overlap (>=85% for titles with >=4 words).
   - Update `lead_exists(url: str, title: str = "", account_id: Optional[int] = None) -> bool`:
     - Checks title duplicate matching against recent existing leads using `is_title_duplicate`.
     - Checks non-generic URL match against `Lead.url`.
2. **Unit Tests (`tests/test_lead_deduplication.py`)**:
   - Verify `normalize_title` and `is_title_duplicate` on real-world tender title variations (e.g., Podegrodzie tender with quotes and dashes).
   - Verify asynchronous `lead_exists` database flow and compatibility with existing `test_tier0_deduplication.py`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.60).
- **Builder (Subagent)**: Implement `normalize_title`, `is_title_duplicate`, and updated `lead_exists` in `src/database.py`, write unit tests in `tests/test_lead_deduplication.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit deduplication math, token overlap precision, zero false-positives on distinct tenders, and generate auditor handshake.
