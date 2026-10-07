# Code Review Guidelines

This document specifies the code review standards for `osint-lead-tracker`. The `om-code-review` and `om-auto-review-pr` skills apply these checks, in addition to human reviewers.

---

## 1. Review Priorities

1. **Correctness & Robustness**:
   - Asynchronous safety: Non-blocking FastAPI event loop. Any blocking I/O (network requests with `requests`, sync scrapers, CPU-bound parsing) MUST be wrapped in `asyncio.to_thread` or executed as async routines.
   - Database operations: All queries must use SQLAlchemy async session patterns (`AsyncSessionLocal`) with proper commits and rollbacks.
   - Lead deduplication: Cross-source duplicate checks must use `lead_exists` with title normalization and token similarity matching.

2. **Security & Secrets Hygiene**:
   - Zero secrets leaks: No API keys (Gemini, OpenRouter, Odoo passwords/tokens) hardcoded in source code or committed files.
   - Authentication & Role access: Validate Bearer tokens and session cookies via dependency injection (`get_current_user`).
   - Input sanitization: URLs and HTML scraped from public platforms must be processed with `DOMSanitizer` before LLM processing.

3. **Data Integrity & Multi-Tenancy**:
   - Campaign isolation: Account filters (`account_id`) must be respected in queries and background jobs.
   - Odoo XML-RPC synchronization: Failures in Odoo syncing must be caught and logged gracefully without terminating the scraper run.

4. **Performance & Token Economy**:
   - Scraper HTML stripping: Boilerplate banners (cookies, GDPR, ads) must be stripped before LLM prompting to prevent token waste.
   - Model selection: Validate that selected models exist in the configured catalog (Gemini / OpenRouter).

---

## 2. Validation Gate

Every pull request must pass the automated validation gate:

```bash
# 1. AST syntax check
python3 -m py_compile src/*.py

# 2. Swarm handshake consistency
python3 scripts/validate-handshakes.py

# 3. Unit test suite
GEMINI_API_KEY=test ODOO_URL=http://test ODOO_DB=test ODOO_USER=test ODOO_API_KEY=test API_TOKEN=test PYTHONPATH=.:src pytest
```

---

## 3. Severity Classification

- **Blocker (Must Fix)**:
  - Security vulnerabilities (exposed secrets, broken auth, SQL injection).
  - Event loop blocking causing UI freezing or server unresponsiveness.
  - Database schema regressions or unhandled exceptions in production pipelines.
  - Broken validation gate or failed unit tests.

- **Major (Needs Attention)**:
  - Missing error handling for scraper network drops or external API failures.
  - Inefficient token usage (>1,000 avoidable tokens per prompt).
  - Missing test coverage for new scrapers or endpoints.

- **Minor / Nit**:
  - Code formatting, docstring improvements, naming conventions.
