# PLAN-042: Fix Missing beautifulsoup4 Dependency & Safe Fallback

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Fix container startup crash caused by missing `beautifulsoup4` in `requirements.txt` and implement safe fallback handling in `DOMSanitizer`.

---

## 🔍 Root Cause Analysis
1. In Plan 041, `from bs4 import BeautifulSoup` was added to `src/scrapers/base.py`.
2. However, `beautifulsoup4` was not added to `requirements.txt`.
3. When running `docker compose build --no-cache && docker compose up -d`, pip installed dependencies strictly from `requirements.txt`, omitting `beautifulsoup4`.
4. On container startup, importing `base.py` threw `ModuleNotFoundError: No module named 'bs4'`, causing Uvicorn to crash and container healthchecks to fail.

---

## 🏗️ Implementation Details
1. **Update `requirements.txt`**:
   - Add `beautifulsoup4>=4.12.0`.
2. **Safe Import & Fallback (`src/scrapers/base.py`)**:
   - Wrap `BeautifulSoup` usage in `DOMSanitizer.clean` with `try...except Exception` to guarantee that missing `bs4` or parsing errors never crash application startup or URL fetching.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.42).
- **Builder (Subagent)**: Update `requirements.txt` and `src/scrapers/base.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit dependency inclusion and safe fallback, verify math/logic, and generate auditor handshake.
