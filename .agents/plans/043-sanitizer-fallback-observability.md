# PLAN-043: Sanitizer Fallback Observability & Diagnostic Status

**Status:** IN_PROGRESS  
**Date:** 2026-07-31  

---

## 🎯 Goal
Provide 100% visibility into DOMSanitizer engine status and active fallbacks so that missing optional packages or fallback triggers are explicitly reported in backend logs, `/api/health`, and the Piaskownica AI Debug Terminal.

---

## 🔍 Architecture & Features
1. **Engine Diagnostics (`src/scrapers/base.py`)**:
   - Add `DOMSanitizer.get_status() -> dict`:
     Returns `{"bs4_available": bool, "active_engine": str, "warning": Optional[str]}`.
   - Log explicit warning on module load if `bs4` is missing.
2. **API Health & Debug Terminal (`src/main.py`)**:
   - Include `sanitizer_status` in `/api/health` response.
   - Include `sanitizer_info` in `sandbox_fetch_url` and Piaskownica test responses so the debug terminal displays:
     `DOM Engine: BS4 + Trafilatura (Optimal)` or `DOM Engine: Trafilatura Fallback (Warning: bs4 missing)`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.43).
- **Builder (Subagent)**: Implement `get_status` and diagnostic reporting in `src/scrapers/base.py` and `src/main.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit status reporting and non-breaking diagnostics, verify math/logic, and generate auditor handshake.
