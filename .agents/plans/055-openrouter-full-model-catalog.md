# PLAN-055: OpenRouter Full Dynamic Model Catalog (400+ Models)

**Status:** IN_PROGRESS  
**Date:** 2026-08-26  

---

## 🎯 Goal
Enable loading the complete, live catalog of 400+ AI models from OpenRouter (including DeepSeek V4 Flash 0731, DeepSeek V4 Pro, Claude, GPT, Llama, Qwen, Mistral, etc.) by querying OpenRouter's public `/api/v1/models` endpoint always (with or without API key), with in-memory caching to keep response times fast and dropdowns fully populated.

---

## 🏗️ Architecture & Implementation Details

### 1. `src/llm_client.py`:
- In `fetch_available_models()`:
  - Query `OPENROUTER_MODELS_URL` (`https://openrouter.ai/api/v1/models`) using `httpx.AsyncClient`.
  - Pass `Authorization: Bearer <OPENROUTER_API_KEY>` if key is present; otherwise make a public request.
  - Implement a lightweight in-memory cache (TTL: 15 minutes) for OpenRouter models list to avoid unnecessary network latency on every page refresh.
  - Filter and sort models nicely (e.g. by name / popularity or provider / id).
  - Include all models like `deepseek/deepseek-v4-flash-0731`, `deepseek/deepseek-v4-pro`, etc.
  - Fallback to `CURATED_OPENROUTER_MODELS` if network fails.

### 2. Frontend UI (`src/static/app.js`):
- Support fast rendering of the comprehensive models list.
- Keep selected model intact if already selected.

### 3. Tests (`tests/test_openrouter_llm.py`):
- Test that `fetch_available_models()` correctly parses full OpenRouter catalog without requiring an API key.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, Swarm governance, git commit/push supervision.
- **Builder (Subagent)**: Implementation in `src/llm_client.py` and tests.
- **Auditor (Subagent)**: Audit and verification.
