# PLAN 057: Dedykowany selektor modeli Gemini dla Google Search Grounding w kontach

**Status:** IN_PROGRESS
**Issue:** #3 (https://github.com/tkogut/osint-lead-tracker/issues/3)
**Date:** 2026-10-08

## 1. Cel
Rozdzielenie konfiguracji modelu do ekstrakcji treści od modelu dedykowanego dla Google Search Grounding. Pozwala to na użycie modeli OpenRouter (np. DeepSeek/Claude) do ekstrakcji, przy jednoczesnym zachowaniu pełnej funkcjonalności Google Grounding przez natywne modele Gemini (np. `gemini-2.5-flash`).

## 2. Architektura i Zakres Zmian
1. **Model & Baza danych (`src/models.py`, `src/database.py`)**:
   - Kolumna `grounding_llm_model = Column(String(100), default="gemini-2.5-flash", nullable=False)` w `Account`.
   - Idempotentna migracja w `init_db()` (`ALTER TABLE accounts ADD COLUMN grounding_llm_model ...`).
2. **Schematy Pydantic (`src/schemas.py`)**:
   - Pole `grounding_llm_model: str = "gemini-2.5-flash"` w `AccountCreate` i `AccountResponse`.
3. **API & OSINT Engine (`src/main.py`, `src/osint_engine.py`)**:
   - Obsługa `grounding_llm_model` w `create_account` i `update_account`.
   - `_search_google` w `OSINTEngine` używa `account.grounding_llm_model` (zawsze z narzędziem GoogleSearch).
4. **Interfejs Użytkownika (`src/static/index.html`, `src/static/app.js`)**:
   - Dedykowany select w modalu edycji konta: `Model Google Search Grounding (Tylko Gemini)`.
   - Obsługa ładowania i zapisu w JS oraz prezentacja na kafelkach kont.
5. **Testy jednostkowe (`tests/test_grounding_model.py`)**:
   - Weryfikacja migracji, zapisu i routingu silnika.

## 3. Podział Zadań (Triada)
- **Coordinator:** Git flow, PR management, weryfikacja handshake.
- **Builder:** Implementacja w kodzie produkcyjnym.
- **Auditor:** Weryfikacja bezpieczeństwa, brak regresji, audyt zgodności matematycznej i typów.
