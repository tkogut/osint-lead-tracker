# PLAN-061: Calibration of Scales and Mass Standards (Wzorcowanie Wag i Wzorców Masy) Campaign Seed

## Cel
Wdrożenie dedykowanej kampanii OSINT "Wzorcowanie Wag i Wzorców Masy" (akredytowane laboratorium PCA / ISO 17025) wraz z kompletem słów kluczowych, kodów CPV oraz zaawansowanym promptem systemowym.
Podczas restartu kontenera na VPS po wdrożeniu przez GitHub Actions (`deploy.yml`), `seed_data()` automatycznie utworzy lub zaktualizuje konto "Wzorcowanie Wag i Wzorców Masy" w SQLite, przypisze dedykowany prompt systemowy, słowa kluczowe i kody CPV oraz zarejestruje wersję w `PromptVersion`.

## Zakres zmian
1. **`src/seed.py`**:
   - Zdefiniowanie `CALIBRATION_PROMPT`, `CALIBRATION_KEYWORDS`, `CALIBRATION_CPVS` na poziomie modułu.
   - W `seed_data()`:
     - Wyszukanie konta o nazwie w `["Wzorcowanie Wag i Wzorców Masy", "Wzorcowanie Wag", "Wzorcowanie wag"]`.
     - Jeśli nie istnieje: utworzenie konta `Wzorcowanie Wag i Wzorców Masy` z pełnymi parametrami, rejestracja `PromptVersion(version=1)`.
     - Jeśli istnieje: aktualizacja `custom_prompt = CALIBRATION_PROMPT`, `target_keywords = json.dumps(CALIBRATION_KEYWORDS)`, scalenie `target_cpvs` z `CALIBRATION_CPVS`, rejestracja `PromptVersion`.
2. **`tests/test_calibration_seed.py`**:
   - Test jednostkowy weryfikujący tworzenie konta od zera.
   - Test jednostkowy weryfikujący aktualizację istniejącego konta (idempotencja, scalanie CPV, zachowanie wersji).
   - Test jednostkowy weryfikujący kompatybilność promptu z `format_prompt_dates()`.

## Role & Handshake
- Builder: Implementacja w `src/seed.py`, testy w `tests/test_calibration_seed.py`, handshake.
- Auditor: Audyt i testy (`pytest`), handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> automatyczny deploy na VPS.
