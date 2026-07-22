# PLAN-019: Rozbudowa Piaskownicy AI o Testowanie URL & Scraperów

**Status:** COMPLETED / DONE  
**Data realizacji:** 2026-07-22  


---

## 🎯 Cel Projektowy
Rozbudowa sekcji Piaskownica AI (`#tab-sandbox`) o możliwość bezpośredniego testowania dedykowanych scraperów i promptów systemowych na żywym adresie URL ogłoszenia przetargowego / zapytania ofertowego (np. z `automatyka.pl`, `logintrade.pl`, `ezamowienia.gov.pl` itp.).

Użytkownik z poziomu panelu UI będzie mógł:
1. Podać bezpośredni link URL do zapytania ofertowego.
2. Pobrać i podglądnąć surową treść wyciągniętą i oczyszczoną z szumu DOM przez `DOMSanitizer` (`curl_cffi` TLS impersonate).
3. Załadować prompt wybranej kampanii z rozwijanej listy.
4. Przeprowadzić test i weryfikację modelu Gemini na żywym ogłoszeniu.

---

## 🏗️ Specyfikacja Zmian

1. **Backend Schemas (`src/schemas.py`)**:
   - `SandboxRequest`: dodanie opcjonalnych pól `url` oraz `raw_text`.
   - `SandboxFetchUrlRequest`: schemat dla edpointu pobierania treści `url`.

2. **Backend API (`src/main.py`)**:
   - `POST /api/sandbox/fetch-url`: pobieranie adresu URL via `curl_cffi` (impersonate "chrome124") i czyszczenie DOM przez `DOMSanitizer.clean`.
   - `POST /api/sandbox/test`: wsparcie automatycznego pobierania z `url` jeśli `raw_text` nie został podany.

3. **Frontend UI (`src/static/index.html` & `src/static/app.js`)**:
   - `#tab-sandbox`: pole `#sandbox-url`, przycisk `#sandbox-fetch-btn` ("Pobierz Treść z URL") oraz dropdown wyboru kampanii do auto-ładowania promptów.
