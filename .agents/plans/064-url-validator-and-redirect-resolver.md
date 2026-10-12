# Plan 064: Automatyczny Walidator Linków i Resolver Przekierowań (URL Validator & Redirect Unpacker)

## 1. Kontekst i Problem
* Podczas skanowania OSINT (w szczególności Google Grounding) modele LLM mogą:
  1. Wygenerować fikcyjny link (halucynacja placeholderów: `123456789`, `987654321`, `gmina-x.pl`).
  2. Przekręcić szyk subdomeny (np. `eb2b.pkpcargo.com` zamiast `pkpcargo.eb2b.com.pl`), co powoduje błąd DNS (NXDOMAIN) i niedziałający link w Odoo.
  3. Zwrócić link przekierowujący Google (`vertexaisearch.cloud.google.com/grounding-api-redirect/...`), który w dotychczasowym kodzie był natychmiast odrzucany w `_parse_leads`, przez co tracone były autentyczne przetargi (np. Elewarr).
* **Cel:** Wprowadzenie dedykowanego modułu `src/url_validator.py`, który weryfikuje poprawność każdego linku przed zapisem do bazy i wysyłką do Odoo, automatycznie rozwija przekierowania do docelowych domen oraz blokuje fałszywe lub martwe adresy.

---

## 2. Architektura Rozwiązania

### Krok 1: Nowy moduł `src/url_validator.py`
* Funkcja główna: `async def validate_and_resolve_url(url: str, timeout: float = 5.0) -> Tuple[bool, str, str]`
  * Zwraca `(is_valid: bool, resolved_url: str, reason: str)`.
* **Warstwa 1: Weryfikacja formatu i filtr placeholderów (Regex/Pattern Check)**
  * Walidacja schematu `http://` / `https://` oraz struktury URL.
  * Blokada znanych sekwencji placeholderów: ciągi `123456789`, `987654321`, `000000`, `gmina-x.pl`, `example.com`, sztuczne ścieżki.
* **Warstwa 2: Weryfikacja DNS (Socket / DNS check)**
  * Asynchroniczne sprawdzenie rozwiązywania nazwy hosta przez `asyncio.get_running_loop().getaddrinfo(hostname, None)`.
  * Jeśli domena nie istnieje w DNS (NXDOMAIN) → odrzucenie z komunikatem *"Błąd DNS: domena nie istnieje w sieci"*.
* **Warstwa 3: Rozwijanie przekierowań Google Vertex AI Search & HTTP Smoke Test**
  * Jeśli URL zawiera `vertexaisearch.cloud.google.com` lub `grounding-api-redirect`:
    * Wykonanie asynchronicznego zapytania `HEAD` (lub lekkiego `GET` z `allow_redirects=True`).
    * Odczytanie nagłówka `Location` lub docelowego adresu URL (`resp.url`) i podmienienie go na czysty, oryginalny link docelowy (np. `https://elewarr.pl/...`).
  * Dla pozostałych linków:
    * Asynchroniczne sprawdzenie statusu HTTP przez `httpx.AsyncClient`:
    * Statusy **200..399** oraz **401, 403** (bramki logowania jak eB2B / ezakupy) → **VALID**.
    * Status **404 / 410** → **INVALID** (*"Błąd HTTP: 404 Strona nie istnieje"*).

### Krok 2: Integracja w `src/osint_engine.py`
* W `_parse_leads`:
  * Zamiast natychmiastowego odrzucania linków z `vertexaisearch` czy `grounding-api-redirect`, wywołanie funkcji rozwijającej przekierowanie lub pozostawienie jej do rozszerzonej walidacji w potoku.
  * Zapewnienie, że sparsowany lead nie zawiera pustych lub jawnie uszkodzonych linków.

### Krok 3: Integracja w `src/main.py` (`run_osint_pipeline`)
* Przed zapisem leada do SQLite i wysłaniem do Odoo:
  * Uruchomienie `validate_and_resolve_url(lead["url"])`.
  * Jeśli link poprawny i rozwinięty: aktualizacja `lead["url"] = resolved_url`.
  * Jeśli link niepoprawny (DNS błąd, 404, placeholder):
    * Wstrzymanie wysyłki do Odoo (ochrona CRM przed śmieciowymi rekordami).
    * Oznaczenie leada jako `pending_approval = True` z ostrzeżeniem w `uzasadnienie` lub pominięcie zapisu.

### Krok 4: Testy jednostkowe `tests/test_url_validator.py`
* Test wykrywania placeholderów (`987654321`, `123456789`, `gmina-x.pl`).
* Test nieistniejącej domeny DNS (np. `non-existent-subdomain-1234567.com`).
* Test rozwijania przekierowania URL (unredirect).
* Test obsługi stron chronionych logowaniem (HTTP 401/403 traktowane jako istniejące serwery).

---

## 3. Kryteria Akceptacji
1. `validate_and_resolve_url` bezbłędnie wykrywa i blokuje domeny z błędami DNS (takie jak `eb2b.pkpcargo.com`).
2. Linki Google Search Grounding (`vertexaisearch.cloud.google.com/grounding-api-redirect/...`) są automatycznie zamieniane na bezpośrednie linki docelowe.
3. Wszystkie testy jednostkowe w `tests/test_url_validator.py` oraz istniejące testy przechodzą z wynikiem 100% PASS.
4. Podwójny handshake Buildera i Auditora w `.agents/swarm/`.
