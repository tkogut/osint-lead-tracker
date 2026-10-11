# PLAN-060: Truck Scales (Wagi Samochodowe) Prompt Update & CPV Expansion

## Cel
Wdrożenie dedykowanego promptu systemowego OSINT dla kampanii "Wagi Samochodowe" oraz rozszerzenie słów kluczowych (PSZOK, wagi 60t, terminale, uelektronicznienie) i kodów CPV (gospodarka odpadami, roboty drogowe, kontrola ruchu, serwisy).
Podczas restartu kontenera po wdrożeniu przez GitHub Actions (`deploy.yml`), `seed_data()` automatycznie zaktualizuje konto "Wagi Samochodowe" w bazie SQLite, załaduje dedykowany prompt systemowy, słowa kluczowe i kody CPV oraz zarejestruje wersję promptu w `PromptVersion`.

## Zakres zmian
1. **`src/seed.py`**:
   - Zdefiniowanie `TRUCK_PROMPT`, `TRUCK_KEYWORDS`, `TRUCK_CPVS`.
   - W `seed_data()`:
     - Sprawdzenie konta `"Wagi Samochodowe"`.
     - Jeśli istnieje: aktualizacja `custom_prompt = TRUCK_PROMPT`, aktualizacja `target_keywords = json.dumps(TRUCK_KEYWORDS)`, scalenie `target_cpvs` z `TRUCK_CPVS`, rejestracja `PromptVersion`.
     - Jeśli nie istnieje: utworzenie z pełną konfiguracją.
2. **`tests/test_truck_seed.py`**:
   - Test jednostkowy weryfikujący poprawne utworzenie/aktualizację konta "Wagi Samochodowe", słowa kluczowe, kody CPV i zgodność promptu z `format_prompt_dates()`.

## Role & Handshake
- Builder: Implementacja w `src/seed.py`, testy w `tests/test_truck_seed.py`, handshake.
- Auditor: Audyt i testy (`pytest`), handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> automatyczny deploy na VPS.
