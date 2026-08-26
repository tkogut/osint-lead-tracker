# PLAN-054: OpenRouter LLM Provider Integration & Unified Model Selection

**Status:** IN_PROGRESS  
**Date:** 2026-08-26  

---

## 🎯 Goal
Enable configuring and using AI models from OpenRouter (https://openrouter.ai/) alongside Google Gemini across the entire application (Campaigns, OSINT pipeline, Scraper extraction, Sandbox, Keyword expansion, and Settings).

---

## 🏗️ Architecture & Implementation Details

### 1. Unified LLM Client (`src/llm_client.py`)
- Standardized `generate_content_with_llm(model, prompt, system_instruction, temperature, max_output_tokens, tools)`:
  - **OpenRouter Routing**: When `model` contains `/` (e.g. `anthropic/claude-3.7-sonnet`, `openai/gpt-4o`, `deepseek/deepseek-chat`, `meta-llama/llama-3.3-70b-instruct`) or explicit provider configuration, calls OpenRouter Chat Completions (`https://openrouter.ai/api/v1/chat/completions`) using `OPENROUTER_API_KEY`.
  - **Google Gemini Routing**: When `model` is `gemini-*`, routes to Google GenAI SDK using `GEMINI_API_KEY`.
  - Standardized token tracking (`input_tokens`, `output_tokens`) and JSON extraction.
- Model discovery `fetch_openrouter_models(api_key)`:
  - Fetches and filters top text models from `https://openrouter.ai/api/v1/models`.

### 2. Settings & Database Auto-seeding (`src/seed.py`)
- Add `OPENROUTER_API_KEY` to the initial settings list.

### 3. API Endpoints (`src/main.py`)
- `GET /api/available-models`:
  - Returns unified list of models containing both Google Gemini and OpenRouter models with provider metadata.
- `POST /api/settings/verify-credentials`:
  - Add verification handler for `scraper="OpenRouter"` (calls `https://openrouter.ai/api/v1/auth/key` or `/api/v1/models`).
- Replace direct `genai.Client` calls in `expand_keywords_via_ai` and `run_sandbox_test` with `llm_client`.

### 4. OSINT Pipeline (`src/osint_engine.py`)
- Update `_evaluate_tier1_with_llm`, `_extract_lead_from_raw_text`, and `_evaluate_gunb_lead` to use `llm_client`.

### 5. Frontend UI (`src/static/app.js`, `src/static/index.html`)
- Settings: Add `OPENROUTER_API_KEY` input with "Testuj Autoryzację" button under the AI category.
- Dropdowns (`#acc-model`, `#sandbox-model`): Group options into `<optgroup label="Google Gemini">` and `<optgroup label="OpenRouter">`.
- Display pretty names and provider badges for models.

### 6. Tests (`tests/test_openrouter_llm.py`)
- Unit tests verifying model routing, OpenRouter API request payload formatting, response parsing, and credential verification.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, Swarm governance, git commit/push supervision.
- **Builder (Subagent)**: Full implementation across backend, frontend, and tests.
- **Auditor (Subagent)**: Audit implementation, verify test suite, and generate auditor handshake.
