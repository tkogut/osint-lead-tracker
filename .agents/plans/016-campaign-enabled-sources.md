# PLAN-016: Konfigurowalne Źródła Wyszukiwania w Kampaniach (Campaign Search Sources)

**Status:** COMPLETED / DONE  
**Data realizacji:** 2026-07-21  

---

## 🎯 Cel Projektowy
Wprowadzenie możliwości decydowania w konfiguracji każdej kampanii (Account), z których źródeł OSINT ma korzystać. Pozwoli to na optymalizację kosztów tokenów API Gemini (poprzez wyłączenie Google Search Grounding dla prostych kampanii z kodami CPV) oraz uniknięcie "pustych przebiegów" (np. szukanie wzorcowań w decyzjach budowlanych GUNB RWDZ).

---

## 🏗️ Specyfikacja Zmian

### 1. Zmiana w Bazie Danych (`src/models.py`, `src/database.py`)
- Dodanie kolumny `enabled_sources` typu `Text` (domyślnie `["BZP", "Google", "GUNB"]` w formacie JSON) do tabeli `accounts`.
- Stworzenie idempotentnej migracji `ALTER TABLE accounts ADD COLUMN enabled_sources TEXT DEFAULT '["BZP", "Google", "GUNB"]'` w `init_db()`.

### 2. Walidacja API i Schematy (`src/schemas.py`)
- Zaktualizowanie schematów `AccountCreate` i `AccountResponse`, aby zawierały pole `enabled_sources: List[str]`.
- Wdrożenie walidatora (Circuit Breaker walidacji), który zablokuje zapis (POST/PUT), jeśli użytkownik odznaczy wszystkie źródła (lista musi mieć co najmniej 1 element). Zwracany błąd: `400 Bad Request`.

### 3. Logika Silnika i Pipeline (`src/main.py`, `src/osint_engine.py`)
- Modyfikacja `run_osint_pipeline`:
  - Pobieramy wybrane źródła z `json.loads(account.enabled_sources)`.
  - Wywołujemy skanowanie tylko dla źródeł obecnych na liście.
  - Wyłączone źródła **nie generują** wpisów w `ResearchLog` oraz `RunPerformanceSnapshot` (aby nie zniekształcać średnich kosztów i wskaźników konwersji).

### 4. Frontend UI (`src/static/index.html`, `src/static/app.js`)
- Dodanie trzech checkboxów (BZP, Google, GUNB) w modalu dodawania i edycji kampanii po lewej stronie (Konfiguracja).
- Dodanie opisów/podpowiedzi kosztowych i przeznaczenia pod każdym checkboxem na froncie:
  - **e-Zamówienia (BZP API)**: *Darmowe. Precyzyjne dla przetargów publicznych.*
  - **Pozwolenia budowlane (GUNB RWDZ)**: *Darmowe. Dobre tylko dla inwestycji budowlanych.*
  - **Wyszukiwarka Google (Grounding)**: *Bardzo drogie (Tokeny Gemini). Szeroki zakres (przetargi prywatne, zapytania).*
- Obsługa zapisywania i ładowania stanu checkboxów w JS.

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator**: Weryfikacja planu po odblokowaniu tokenów, merge i deploy.
- **Builder**: Modyfikacja modeli, API, silnika i interfejsu UI.
- **Auditor**: Audyt poprawności zapisu JSON do SQLite i walidacji braku źródeł (Zero-Source block).
