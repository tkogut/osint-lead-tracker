# PLAN-020: Rozbudowa Piaskownicy AI o Wybór Źródła Wyszukiwania (BZP, GUNB, Google, Scrapery) & Naprawę Ładowania Kampanii

**Status:** IN_PROGRESS  
**Data dodania:** 2026-07-22  

---

## 🎯 Cel Projektowy
Naprawienie automatycznego ładowania listy kampanii w Piaskownicy AI oraz wdrożenie uniwersalnej opcji **Wyboru Źródła Wyszukiwania** (`source`), pozwalającej testować dowolne źródło OSINT (`BZP`, `GUNB`, `Google Search Grounding`, `Automatyka`, `Logintrade`, `DOMSanitizer`).

---

## 🏗️ Specyfikacja Zmian

1. **Backend Schemas (`src/schemas.py`)**:
   - `SandboxRequest`: pole `source: Optional[str]`.
   - `SandboxFetchUrlRequest`: pole `source: Optional[str]`.

2. **Backend API (`src/main.py`)**:
   - `POST /api/sandbox/fetch-url`: obsługa wybranego `source` (wtyczki scraperów, API BZP dla linków ogłoszeń itp.).
   - `POST /api/sandbox/test`: obsługa `source == "Google"` z aktywacją narzędzia `google_search` (Search Grounding).

3. **Frontend UI (`src/static/index.html` & `src/static/app.js`)**:
   - `index.html`: dodanie rozwijanej listy wyboru źródła wyszukiwania `#sandbox-source-select`.
   - `app.js`: poprawka inicjalizacji `populateSandboxCampaigns()`, obsługa `populateSandboxSources()` z `GET /api/sources` oraz przekazywanie `source` do backendu.
