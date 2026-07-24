# PLAN-041: Integrate Playwright for Automatyka.pl

**Status:** IN_PROGRESS  
**Date:** 2026-07-24  

---

## 🎯 Goal
Enable full JavaScript rendering and authenticated contact details retrieval for Automatyka.pl within the LLM Sandbox and daily scraper execution using Playwright headless browser with cookie replication from the xtech.pl login session.

## 📋 Steps
1. **Requirements & Packages**:
   - Add `playwright>=1.44` to `requirements.txt`.
   - Update `Dockerfile` to install Chromium system dependencies and run `playwright install chromium` as `appuser`.
2. **Playwright Fetcher Helper**:
   - Create `src/scrapers/playwright_fetcher.py` with `fetch_with_playwright(url, user, pwd)` using the multi-step login, cookies extraction, duplication for `.automatyka.pl` domain, and page content retrieval.
3. **Sandbox Integration**:
   - Integrate `fetch_with_playwright` into `sandbox_fetch_url()` and `run_sandbox_test()` in `src/main.py` when the context or scraper is identified as `"Automatyka"`.
4. **Scraper Pipeline Integration**:
   - Optionally update `AutomatykaScraper` in `src/scrapers/automatyka.py` to use `fetch_with_playwright` for notice details, so daily scans fetch full contact information.

---
