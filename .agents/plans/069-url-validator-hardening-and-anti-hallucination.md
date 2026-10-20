# PLAN-069: Uszczelnienie walidatora linków (URL Validator Hardening) i ochrona przed halucynacjami AI

## Cel
Wyeliminowanie ryzyka przenikania zsyntetyzowanych / zhalucynowanych leadów z Google Search Grounding (np. zmyślonych adresów typu `https://platformazakupowa.smakpol.pl/zapytanie/12345` z placeholderami `12345` i zaparkowanymi domenami) do bazy danych i systemu CRM Odoo.
Dodatkowo: bezpieczne usunięcie fałszywego leada #81 z bazy produkcyjnej na VPS.

## Zakres zmian

### 1. `src/url_validator.py`
- **Rozszerzenie `PLACEHOLDER_REGEXES`**:
  - Wykrywanie sekwencji testowych: `\b12345\b`, `/12345`, `12345$`, `\b54321\b`.
  - Wykrywanie zmyślonych subdomen platform przetargowych:
    - `r"platformazakupowa\.[a-z0-9\-]+\.pl"` (prawidłowa Platforma Zakupowa to `platformazakupowa.pl` lub subdomeny w domenie `platformazakupowa.pl`, np. `*.platformazakupowa.pl`, a NIE `platformazakupowa.<inna_domena>.pl`).
    - `r"ezamowienia\.[a-z0-9\-]+\.pl"` (prawidłowe e-Zamówienia to `ezamowienia.gov.pl`).
    - `r"bazakonkurencyjnosci\.[a-z0-9\-]+\.pl"`.
  - Wykrywanie zmyślonych ścieżek placeholderów: `r"/zapytani[ea]/1234"`, `r"/przetargi?/1234"`.
- **Wykrywanie zaparkowanych domen (Parked IP Detection)**:
  - Sprawdzenie IP zwróconego przez `_resolve_dns`: odrzucanie znanych IP parkingowych (np. `104.247.81.*`, `34.102.136.*`, `199.59.243.*`, `0.0.0.0`, `127.*`).
- **Zaostrzenie HTTP Smoke Test**:
  - Zmiana polityki w przypadku błędu połączenia (`ConnectError`, `SSL_ERROR_SYSCALL`, `ConnectTimeout`):
    - Zamiast pobłażliwego `is_valid = True, "OK (Host reachable)"`, dla nieznanych domen i błędów SSL/odrzucenia połączenia walidator zwraca **`is_valid = False`** z powodem błędu (np. `Nieosiągalny host / Błąd SSL`).
    - Dzięki temu żaden niezweryfikowany link nie trafia do Odoo jako prawidłowy.

### 2. `src/osint_engine.py` i `src/seed.py`
- Wzmocnienie reguły anty-halucynacyjnej w promptach systemowych:
  - "BEZWZGLĘDNY ZAKAZ generowania fikcyjnych adresów URL, zmyślonych subdomen (np. platformazakupowa.nazwa-firmy.pl) i numerów testowych (np. /12345). Każdy podany adres URL MUSI fizycznie istnieć w zwróconych wynikach wyszukiwania. Jeśli brak rzeczywistego linku, zwróć pustą tablicę leadów."

### 3. Czyszczenie bazy produkcyjnej na VPS
- Usunięcie fałszywego leada #81 (`Zakład Mięsny "Smakpol" Sp. z o.o.`) z tabeli `leads` w bazie produkcyjnej.

### 4. `tests/test_url_validator_hardening.py`
- Test odrzucenia URL `https://platformazakupowa.smakpol.pl/zapytanie/12345`.
- Test odrzucenia sekwencji `12345` i `54321`.
- Test odrzucenia fikcyjnych subdomen `platformazakupowa.firma.pl`.
- Test odrzucenia błędów połączenia SSL i zaparkowanych domen.
- Test akceptacji legalnych URL (`https://ezamowienia.gov.pl/...`, `https://platformazakupowa.pl/...`).

## Role & Handshake
- Builder: Implementacja w `src/url_validator.py`, `src/osint_engine.py`, `src/seed.py`, testy w `tests/test_url_validator_hardening.py`, wygenerowanie handshake Buildera.
- Auditor: Audyt jakościowy, bezpieczeństwa i testy (`pytest`), wygenerowanie handshake Auditora.
- Coordinator: Czyszczenie bazy VPS, push do `main` przez `smart_commit.sh` -> automatyczne wdrożenie na VPS.
