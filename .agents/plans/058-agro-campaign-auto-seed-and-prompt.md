# PLAN-058: Agro Campaign Auto-Seed and OSINT System Prompt

## Cel
Wdrożenie automatycznego seedowania / aktualizacji kampanii "Agro" (Analizatory NIR, Wilgotnościomierze i Automatyczne Próbniki Ziarna) w `src/seed.py` na środowisku produkcyjnym (VPS) oraz lokalnym.
Podczas restartu kontenera po wdrożeniu przez GitHub Actions (`deploy.yml`), `seed_data()` automatycznie utworzy lub zaktualizuje konto "Agro" w bazie SQLite, załaduje dedykowany prompt systemowy, słowa kluczowe i kody CPV oraz zarejestruje wersję promptu w `PromptVersion`.

## Zakres zmian
1. **`src/seed.py`**:
   - Zdefiniowanie stałej `AGRO_PROMPT` zawierającej pełny schemat OSINT silnika (klauzule dat, zakaz redirectów, filary NIR i Próbników Ziarna, format JSON).
   - Zdefiniowanie `AGRO_KEYWORDS` i `AGRO_CPVS`.
   - W `seed_data()`: sprawdzenie, czy istnieje konto o nazwie `"Agro"`.
   - Jeśli nie istnieje: utworzenie rekordu `Account` z `name="Agro"`, `custom_prompt=AGRO_PROMPT`, `target_keywords`, `target_cpvs`, `llm_model="gemini-2.5-flash"`, `grounding_llm_model="gemini-2.5-flash"`, `enabled_sources=["BZP", "Google", "GUNB", "Automatyka", "BazaKonkurencyjnosci", "BiznesPolska", "LoginTrade", "PlatformaZakupowa"]`, `is_active=True`.
   - Jeśli istnieje: upewnienie się, że `custom_prompt` jest zaktualizowany.
   - Sprawdzenie/zapisanie rekordu w `PromptVersion` powiązanego z tym kontem.
2. **`tests/test_agro_seed.py`**:
   - Test jednostkowy weryfikujący, że `seed_data()` tworzy konto "Agro", poprawnie zapisuje słowa kluczowe, CPV oraz prompt zgodny z `format_prompt_dates`.

## Role & Handshake
- Builder: Implementacja zmian w `src/seed.py` oraz testów `tests/test_agro_seed.py`. Wygenerowanie Builder handshake.
- Auditor: Audyt bezpieczeństwa i poprawności, uruchomienie testów (`pytest`), wygenerowanie Auditor handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> wyzwolenie automatycznego deployu na VPS w GitHub Actions.
