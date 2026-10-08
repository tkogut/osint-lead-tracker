# Execution Plan: Dedicated Gemini Model Selector for Google Search Grounding in Accounts

**Goal:** Decouple Google Search Grounding model selection from content extraction LLM selection in account settings, allowing accounts to use OpenRouter models (e.g. DeepSeek/Claude) for content parsing while Google Search Grounding continues to function with a dedicated native Gemini model.
**Issue:** #3 (link: https://github.com/tkogut/osint-lead-tracker/issues/3)
**Date:** 2026-10-08
**Engine:** om-auto-create-pr (steps: 8, --loop: no)

## Scope
- Database: Add `grounding_llm_model` column to `Account` table with safe SQLite migration in `init_db()`.
- Backend Schemas: Add `grounding_llm_model: str = "gemini-2.5-flash"` to `AccountCreate` and `AccountResponse`.
- Backend Engine: Update `OSINTEngine._search_google` to use `account.grounding_llm_model`.
- Backend API: Update `create_account` and `update_account` endpoints in `src/main.py` and provide available Gemini grounding models.
- Frontend: Add dedicated "Model Google Search Grounding (Tylko Gemini)" dropdown in `#account-modal` in `src/static/index.html` and wire it in `src/static/app.js`.
- Testing: Add unit and integration tests verifying schema, persistence, and engine routing.

## Non-goals
- Adding third-party search providers (e.g. Bing or Tavily).
- Changing how other scraper plugins (BiznesPolska, Logintrade, etc.) utilize extraction models.

## Risks & Mitigations
- **SQLite Schema Migration:** Existing databases on VPS must upgrade without loss of data.
  *Mitigation:* Idempotent `ALTER TABLE accounts ADD COLUMN grounding_llm_model ...` in `database.init_db()` wrapped in try/except.
- **Backward Compatibility:** Accounts created without `grounding_llm_model` must default to `"gemini-2.5-flash"`.
  *Mitigation:* Pydantic field defaults and SQL default value ensure zero disruption.

## Progress

PR: #4 (link: https://github.com/tkogut/osint-lead-tracker/pull/4)

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Database and Schema Migration

- [x] 1.1 Add grounding_llm_model column to Account model in src/models.py — ca66d87
- [x] 1.2 Implement idempotent SQLite migration in src/database.py — ca66d87
- [x] 1.3 Update AccountCreate and AccountResponse schemas in src/schemas.py — ca66d87

### Phase 2: Backend API and Engine Routing

- [x] 2.1 Update account CRUD endpoints in src/main.py — ca66d87
- [x] 2.2 Route Google Search Grounding to grounding_llm_model in src/osint_engine.py — ca66d87

### Phase 3: Frontend UI Integration

- [x] 3.1 Add Gemini grounding model selector in src/static/index.html — ca66d87
- [x] 3.2 Wire grounding model in modal logic and cards in src/static/app.js — ca66d87

### Phase 4: Validation and Tests

- [x] 4.1 Implement unit tests in tests/test_grounding_model.py — ca66d87
- [x] 4.2 Run full validation gate and test suite — ca66d87
