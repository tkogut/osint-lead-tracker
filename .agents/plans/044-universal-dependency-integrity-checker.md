# PLAN-044: Universal System Dependency Integrity & Health Diagnostics

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Implement a universal, automated system dependency scanner (`dependency_checker.py`) that checks ALL required and optional Python packages at startup, logs explicit warning/critical banners, and exposes health diagnostics via `/api/health`.

---

## 🔍 Architecture & Features
1. **`src/dependency_checker.py`**:
   - `audit_dependencies() -> dict`: Automatically scans all 11 system dependencies (`fastapi`, `uvicorn`, `pydantic_settings`, `apscheduler`, `aiosqlite`, `google.genai`, `sqlalchemy`, `curl_cffi`, `trafilatura`, `bs4`, `playwright`).
   - Distinguishes required vs optional packages.
   - Emits structured warnings (`MISSING`, `ERROR`, `DEGRADED`) and version numbers.
   - Logs prominent startup banner during FastAPI lifespan event.
2. **Integration in `src/main.py`**:
   - Call `audit_dependencies()` on startup.
   - Include complete `dependencies` report in `GET /api/health`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.44).
- **Builder (Subagent)**: Implement `src/dependency_checker.py` and hook into `src/main.py` lifespan & `/api/health`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit dependency scanning logic, verify unit tests and math/logic, and generate auditor handshake.
