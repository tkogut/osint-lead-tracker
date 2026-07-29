# PLAN-036: Fix Campaign Save Event Loop Freeze & Container Restart

**Status:** IN_PROGRESS  
**Date:** 2026-07-29  

---

## 🎯 Goal
Fix the bug where saving or updating a campaign (`PUT /api/accounts/{id}` or `POST /api/accounts`) freezes the server event loop, causing container timeout/restart and redirecting the user to the login screen.

---

## 🔍 Root Cause Analysis
In `src/main.py`, both `create_account` and `update_account` call `await expand_keywords_via_ai(req.target_keywords)`.
Inside `expand_keywords_via_ai`, `client.models.generate_content(...)` (Google GenAI Python SDK) is called **synchronously** inside an `async def` function without offloading to a threadpool.
When Gemini API latency or network calls occur, it blocks FastAPI's single-threaded event loop for 5-15+ seconds. Docker healthchecks fail or Uvicorn worker hangs, triggering a container restart/reset and redirecting the browser to the login window.

---

## 🏗️ Implementation Details
1. **Non-Blocking Threadpool Execution (`src/main.py`)**:
   - Refactor `expand_keywords_via_ai` to run `client.models.generate_content` in a worker thread using `asyncio.to_thread`.
   - Wrap thread execution in `asyncio.wait_for(..., timeout=5.0)` so if Gemini API is slow or times out, it gracefully logs a warning and returns original keywords within 5 seconds without blocking event loop or crashing the server.
2. **Sandbox LLM Isolation (`src/main.py`)**:
   - Refactor `run_sandbox_test` to offload `generate_content` to `asyncio.to_thread` with a 30.0s timeout.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.14).
- **Builder (Subagent)**: Offload synchronous SDK calls to worker threads in `src/main.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit event loop non-blocking behavior, verify math/logic, and generate auditor handshake.
