# PLAN-025: Flexible Investor Context Extraction & Active Scraper Fallback

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Improve LLM lead extraction rules in `src/osint_engine.py` and `src/main.py` so that:
1. **Investor Extraction**: If no explicit corporate header exists in raw text, Gemini must infer the investor/zamawiający from text context (e.g. factory names, plant locations like `Zakład Produkcyjny "Pomorze" i "Mazowsze"`).
2. **Active Offer Assumption for Scraper Items**: If no explicit deadline date string is present in scraped raw text, assume the notice is ACTIVE as long as publication/generation date is within the valid search window (do not reject with `{"leady": []}`).
3. **Sandbox & Engine Alignment**: Ensure Piaskownica AI extraction instructions in `src/main.py` match the upgraded extraction rules in `src/osint_engine.py`.

---

## 🏗️ Implementation Details
- Update `_extract_lead_from_raw_text` and `get_system_instruction` in `src/osint_engine.py`:
  - Add explicit rules for inferring `inwestor` from context (plant, facility, division names).
  - Clarify that scraped items without explicit closing dates should be treated as active if published within the current date window.
- Update `run_sandbox_test` prompt template in `src/main.py` to match the enhanced rules.

---

## 🛠️ Roles
- **Coordinator**: Plan creation, delegating build task to Builder subagent, handshake validation, smart commit.
- **Builder (Subagent)**: Modify `src/osint_engine.py` and `src/main.py`, run syntax checks, generate builder handshake JSON.
