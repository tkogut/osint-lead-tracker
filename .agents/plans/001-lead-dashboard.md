# PLAN-001: Lead Dashboard Architecture & Implementation

## 🎯 Cel Biznesowy
Umożliwienie użytkownikowi zarządzania wieloma kampaniami/produktami (multi-tenancy), monitorowania każdego uruchomienia skanera (twarde dowody wykonania), weryfikacji i edycji promptów LLM w bezpiecznym piaskownicy (Sandbox) oraz zarządzania konfiguracją systemową z poziomu nowoczesnego panelu webowego (GUI).

---

## 🏗️ Specyfikacja Techniczna i Procesowa

### 1. Architektura Danych (Multi-tenancy & Logs)
* **Izolacja danych (Konta)**: Każde konto (`Account`) reprezentuje osobną kampanię (np. "Wagi Samochodowe", "Maszyny Przemysłowe"). Zawiera dedykowane parametry wyszukiwania (kody CPV, słowa kluczowe), spersonalizowany prompt systemowy oraz ustawienia modelu LLM.
* **Twarde Dowody Researchu (`ResearchLog`)**: Zapis każdego żądania do BZP API, GUNB lub Google Search.
  * Zapisujemy: `timestamp`, `source`, `query_params` (JSON), `raw_response_hash` (skrót SHA-256 z odpowiedzi w celu weryfikacji integralności danych), `response_status_code` oraz `log_text` (np. kod błędu, logi pre-filtra).
  * Log powstaje **zawsze**, nawet gdy liczba znalezionych leadów wynosi 0.

### 2. Panel Ustawień & Auth
* Autoryzacja sesyjna (cookie) oparta na mechanizmie login/hasło. Hasła są solone i hashowane przy użyciu algorytmu PBKDF2-SHA256 (analogicznie do bazy baseline z `linkedin-tracker`).
* GUI daje pełny dostęp do mapowania zmiennych środowiskowych `.env` zapisanych w bazie danych (np. klucze API Gemini, Odoo URL, Odoo API Key).

### 3. LLM Engine & Sandbox (Piaskownica)
* Wyszukiwanie w `osint_engine.py` zostaje sparametryzowane. Zamiast czytać zmienne globalne, silnik przyjmuje instancję `Account`.
* Sandbox udostępnia endpoint `POST /api/sandbox/test`, który pozwala na przesłanie dowolnego fragmentu tekstu ogłoszenia (np. z BZP) wraz z edytowanym w GUI promptem w celu przetestowania odpowiedzi modelu bez wpływu na produkcyjną bazę Odoo.

---

## 🛠️ Ścieżki Operacyjne dla Buildera (Git Worktrees)

Sugerowane pliki do utworzenia/edycji:
1. `src/models.py` (Nowy): Definicja modeli SQLAlchemy (`Account`, `ResearchLog`, `User`, `Setting`).
2. `src/database.py` (Edycja): Dodanie konfiguracji sesji SQLAlchemy (synchronicznej i asynchronicznej).
3. `src/schemas.py` (Nowy): Definicje walidacyjne Pydantic dla operacji CRUD.
4. `src/osint_engine.py` (Edycja): Refaktoryzacja metod `run_search` i `_verify_bzp_notice` pod kątem dynamicznych parametrów konta oraz zapisu logów researchu.
5. `src/main.py` (Edycja): Dodanie tras uwierzytelniania, endpointów API dla kont, logów, piaskownicy oraz serwowania plików statycznych GUI.
6. `src/static/` (Nowy katalog): Pliki frontendu (`index.html`, `styles.css`, `app.js`) realizujące estetyczny interfejs Single Page Application (SPA).

---

## 🔎 Punkty Kontrolne i Kryteria Testowe dla Auditora

1. **Math-Consistency & Hash Validation**:
   * Czy każdy log researchu generuje unikalny skrót SHA-256 (`raw_response_hash`) z odpowiedzi serwera?
   * Czy baza poprawnie zapisuje statusy 200/500/404 z zewnętrznych API?
2. **Izolacja Kont (Multi-tenancy)**:
   * Czy uruchomienie skanowania dla Konta A (np. CPV wagi) nie miesza się z wynikami dla Konta B (np. inne CPV)?
   * Czy klucze Odoo i Odoo Team ID są poprawnie mapowane per konto?
3. **Bezpieczeństwo sesji**:
   * Czy próba wejścia na API bez ciasteczka sesyjnego zwraca poprawny błąd `401 Unauthorized`?
   * Czy hasła są zabezpieczone solą i PBKDF2?
