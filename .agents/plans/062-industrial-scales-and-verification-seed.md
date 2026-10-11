# PLAN-062: Industrial Scales and Verification (Wagi Przemysłowe i Legalizacja Wag) Campaign Seed

## Cel
Wdrożenie nowej kampanii OSINT "Wagi Przemysłowe" (wagi platformowe, pomostowe, zbiornikowe, silosowe, paletowe, hakowe, dozujące, ATEX oraz usługi legalizacji wag samochodowych, platformowych, paletowych i hakowych) wraz z kompletem 41 słów kluczowych, 10 kodów CPV oraz zaawansowanym promptem systemowym.
Podczas restartu kontenera na VPS po wdrożeniu przez GitHub Actions (`deploy.yml`), `seed_data()` automatycznie utworzy lub zaktualizuje konto "Wagi Przemysłowe" w SQLite, przypisze dedykowany prompt systemowy, słowa kluczowe i kody CPV oraz zarejestruje wersję w `PromptVersion`.

## Zakres zmian
1. **`src/seed.py`**:
   - Zdefiniowanie `INDUSTRIAL_PROMPT`, `INDUSTRIAL_KEYWORDS`, `INDUSTRIAL_CPVS` na poziomie modułu.
   - W `seed_data()`:
     - Wyszukanie konta o nazwie w `["Wagi Przemysłowe", "Waga Przemysłowa"]`.
     - Jeśli nie istnieje: utworzenie konta `Wagi Przemysłowe` z pełnymi parametrami, rejestracja `PromptVersion(version=1)`.
     - Jeśli istnieje: aktualizacja `custom_prompt = INDUSTRIAL_PROMPT`, `target_keywords = json.dumps(INDUSTRIAL_KEYWORDS)`, scalenie `target_cpvs` z `INDUSTRIAL_CPVS`, rejestracja `PromptVersion`.
2. **`tests/test_industrial_seed.py`**:
   - Test jednostkowy weryfikujący tworzenie konta od zera.
   - Test jednostkowy weryfikujący aktualizację istniejącego konta (idempotencja, scalanie CPV, zachowanie wersji).
   - Test jednostkowy weryfikujący kompatybilność promptu z `format_prompt_dates()`.

## Role & Handshake
- Builder: Implementacja w `src/seed.py`, testy w `tests/test_industrial_seed.py`, handshake.
- Auditor: Audyt i testy (`pytest`), handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> automatyczny deploy na VPS.
