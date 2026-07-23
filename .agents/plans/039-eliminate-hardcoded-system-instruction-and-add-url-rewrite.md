# PLAN-039: Eliminate Hardcoded System Instruction & Add Automatyka URL Rewrite

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
1. Eliminate the hardcoded global system instruction ("Wagi Samochodowe") fallback when a campaign has different targets or its own parameters. Always use campaign's active custom prompt or generate a dynamic one using target keywords/name.
2. Fix `_extract_lead_from_raw_text` and `_verify_bzp_notice` in `osint_engine.py` to strictly pass the campaign's system instruction via `system_instruction` API parameter, instead of prepending it to user prompt or mixing it with hardcoded truck scale text.
3. Implement automatic URL rewrite in Sandbox (both `/api/sandbox/fetch-url` and `/api/sandbox/test`) for Automatyka.pl links containing `?topId=ID` to fetch the actual logged-in details URL: `https://www.automatyka.pl/firm-profilepl/offerrequestpl/viewrfqpl/{ID}`.

---

## 🏗️ Implementation Details

### 1. Dynamic System Instruction (`src/osint_engine.py`)
- Refactor `get_system_instruction(today_str: str, start_str: str, account: Optional[Any] = None) -> str`:
  - If `account` has `custom_prompt`, return formatted custom prompt.
  - If `account` has no `custom_prompt`, build a dynamic default system instruction based on `account.name` and parsed `account.target_keywords`, avoiding hardcoding "wagi samochodowe" for other campaigns.
- In `_extract_lead_from_raw_text` and `_verify_bzp_notice`:
  - Pass the custom/dynamic instruction strictly as `system_instruction` in the GenerateContentConfig.
  - Keep the user `prompt` text clean of the hardcoded truck scale criteria, specifying only the technical parsing instructions and the JSON output format.

### 2. URL Rewrite Helper (`src/main.py` & `src/scrapers/automatyka.py`)
- Add a helper function to detect and rewrite Automatyka URLs:
  - If URL contains `automatyka.pl` and `topId=([0-9]+)`, extract `ID` and rewrite to:
    `https://www.automatyka.pl/firm-profilepl/offerrequestpl/viewrfqpl/{ID}`
- Integrate this helper into `/api/sandbox/fetch-url` and `/api/sandbox/test` (in `main.py`) to fetch the full details page under authenticated scraper session.
- Add `scraper: Optional[str] = "Auto"` to `SandboxRequest` in `src/schemas.py` and align the fetching logic in `run_sandbox_test()` in `src/main.py`.

---

## 🛠️ Roles
- **Coordinator**: Create plan, validate handshakes, execute commit.
- **Builder (Subagent)**: Implement backend changes in `osint_engine.py`, `schemas.py`, `main.py`, verify syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit changes, verify prompt resolution logic, test URL rewrite under logged-in session, and generate auditor handshake.
