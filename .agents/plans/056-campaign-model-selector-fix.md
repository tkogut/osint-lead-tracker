# PLAN-056: Campaign Model Selector & OpenRouter Models Full Integration

**Status:** IN_PROGRESS  
**Date:** 2026-08-27  

---

## 🎯 Goal
Ensure that the Campaign creation and editing modal (`#acc-model`) always populates and displays all available models (both Google Gemini and the full OpenRouter catalog with `<optgroup>` groupings), correctly restores selected models, prevents fallback to hardcoded options, and fixes model validity badge checks on campaign cards.

---

## 🏗️ Architecture & Implementation Details

### 1. Reusable Model Populator (`src/static/app.js`)
- Implement `populateModelSelect(selectEl, selectedValue)`:
  - Supports `<optgroup label="Google Gemini">` and `<optgroup label="OpenRouter">`.
  - Maps model IDs and display names cleanly.
  - Dynamically appends custom/inactive models if not found in list.
  - Sets selected value properly.
- In `openAccountModal(accountId = null)`:
  - Always execute `populateModelSelect(accModelSelect, acc ? acc.llm_model : "gemini-2.5-flash")` when opening the modal.
  - If `availableModelsList` is empty, await `loadAvailableModels()` first.
- In `renderAccounts(accounts)`:
  - Fix `isModelValid` calculation using `validIds` (`availableModelsList.map(m => (typeof m === 'object' && m.id) ? m.id : m)`) so OpenRouter model names on campaign cards are not falsely marked as "(Nieobsługiwany!)".
- In `loadAvailableModels()`:
  - Use `populateModelSelect()` for `#sandbox-model`, `#acc-model`, and `#setting-GOOGLE_LLM_MODEL`.

### 2. Frontend HTML Template (`src/static/index.html`)
- In `#acc-model` select (lines 512-518):
  - Remove hardcoded static `<option>` tags to prevent initial or form-reset flash of old Gemini-only options.

### 3. Verification & Tests (`tests/test_openrouter_llm.py`, `frontend-tests/unit/kpi.test.js`)
- Run backend and frontend unit tests to verify no regressions.
- Verify dual handshake protocol and deploy to VPS.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, governance, git commit/push.
- **Builder (Subagent)**: Implement fixes in `src/static/app.js` and `src/static/index.html`.
- **Auditor (Subagent)**: Audit changes and execute test suites.
