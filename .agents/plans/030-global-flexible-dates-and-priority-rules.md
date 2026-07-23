# PLAN-030: Global Flexible Date Rules & Priority Classification for Leads

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Upgrade LLM prompt instructions globally across all engine functions (`_extract_lead_from_raw_text`, `get_system_instruction`) and `run_sandbox_test` in `src/main.py` so that:
1. **Topic Relevance as Primary Criterion**: If the content matches the campaign domain (e.g. scale calibration, purchase with calibration, maintenance), the inquiry is ALWAYS treated as a valuable lead.
2. **Flexible Date Handling (No Hard Rejections for Missing Dates)**: Absence of explicit publication or submission deadline dates in scraped text MUST NOT cause lead rejection (`ODRZUĆ` / `{"leady": []}`). If missing, assume active status.
3. **Smart Priority Grading**:
   - `wysoki`: Full details present (explicit future deadline, clear investor name, detailed scope).
   - `sredni`: Clear scope and contact info, minor details missing.
   - `niski`: Short inquiry or missing explicit deadline/dates, but topic strictly matches campaign scope.

---

## 🏗️ Implementation Details
1. **Engine (`src/osint_engine.py`)**:
   - Update `_extract_lead_from_raw_text` and `get_system_instruction` with global rules for topic relevance, date fallback, and smart priority assignment (`wysoki`/`sredni`/`niski`).
2. **Sandbox Endpoint (`src/main.py`)**:
   - Update prompt requirements in `run_sandbox_test` to reflect the global rules identically.
3. **Tests (`tests/`)**:
   - Add/update test cases verifying that short date-less inquiries (e.g. Sartorius calibration request) return a valid lead with `priorytet: niski`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, script integration, handshake validation, smart commit (auto bump to v1.7.8).
- **Builder (Subagent)**: Implement prompt rules in `src/osint_engine.py` and `src/main.py`, update unit tests, verify syntax, and generate builder handshake.
