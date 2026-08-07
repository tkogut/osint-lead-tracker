# PLAN-052: Google Search Grounding Global Model Setting

**Status:** IN_PROGRESS  
**Date:** 2026-08-07  

---

## 🎯 Goal
Move the Google Search Grounding LLM model configuration from the individual campaign/account level to the global settings panel under `GOOGLE_LLM_MODEL`. This prevents conflicts and allows central management of the Gemini search model.

---

## 🏗️ Implementation Details

### 1. Database Setting Seeding (`src/seed.py`)
- Add `"GOOGLE_LLM_MODEL"` to the `setting_keys` list.
- Define a default value of `"gemini-2.5-flash"` for the `GOOGLE_LLM_MODEL` setting.

### 2. Frontend Settings UI (`src/static/app.js`)
- Add `"GOOGLE_LLM_MODEL"` to the AI category keys in `renderSettings()`.
- Add a user-friendly label for `"GOOGLE_LLM_MODEL"` in the `labelMap`: `"Model AI dla Google Search Grounding"`.

### 3. Google Scraper Integration (`src/osint_engine.py`)
- Modify the `_search_google()` function to load the model dynamically from settings using `get_db_setting_sync("GOOGLE_LLM_MODEL", "gemini-2.5-flash")` instead of `account.llm_model`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, push supervision.
- **Builder (Subagent)**: Implement code changes in `seed.py`, `app.js`, and `osint_engine.py`.
- **Auditor (Subagent)**: Review implementation and verify that calculations and settings work correctly.
