# PLAN-053: Make Google LLM Model Setting a Select Dropdown

**Status:** IN_PROGRESS  
**Date:** 2026-08-07  

---

## 🎯 Goal
Replace the plain text input field for `GOOGLE_LLM_MODEL` in the Settings panel with a dynamic `<select>` dropdown populated from available Gemini models (`/api/available-models`).

---

## 🏗️ Implementation Details

### Frontend UI (`src/static/app.js`)
1. In `renderField(key, value)`:
   - When `key === "GOOGLE_LLM_MODEL"`, render a `<select id="setting-GOOGLE_LLM_MODEL" data-key="GOOGLE_LLM_MODEL">` dropdown displaying model options with pretty names.
2. In `loadAvailableModels()`:
   - Include `document.getElementById("setting-GOOGLE_LLM_MODEL")` in the list of select elements populated when available models are fetched.
3. In `settingsForm.addEventListener("submit", ...)`:
   - Query both `input[data-key]` and `select[data-key]` elements so select changes are saved to `/api/settings`.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, push supervision.
- **Builder (Subagent)**: Implement code changes in `src/static/app.js`.
- **Auditor (Subagent)**: Audit implementation and verify E2E & frontend tests.
