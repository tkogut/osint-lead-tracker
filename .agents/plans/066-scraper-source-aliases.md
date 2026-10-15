# Plan 066: Scraper Source Name Aliases & Normalization (Fix #5)

## Goal
Eliminate 404 scan errors caused by casing variations, domain suffixes, or typos in scraper source names (e.g. `LoginTrade` vs `Logintrade`, `BazaKonkurencyjnosci` vs `BazaKonkurenconosci`), ensuring every configured source resolves reliably. Fixes #5.

## Architecture & Implementation
1. **`src/scrapers/factory.py`**:
   - `normalize_source_name(name: str) -> str`: strip whitespace, lowercase, remove suffixes (`.gov.pl`, `.pl`, `.com`), strip non-alphanumeric chars.
   - `SCRAPER_REGISTRY`: add aliases (`LoginTrade`, `BazaKonkurencyjnosci`, `Biznes-Polska`, etc.).
   - `get_scraper_for_source(source_name: str) -> Optional[BaseScraper]`: exact match first, then normalized mapping.
2. **`src/osint_engine.py`**:
   - `scan_all_sources`: normalize built-in sources (`bzp` / `ezamowienia` -> `BZP`, `google` -> `Google`, `gunb` -> `GUNB`).
3. **`src/main.py` & `src/seed.py`**:
   - Canonical normalization on account creation/update.
   - Safe idempotent migration in `init_db()` or `seed_data()` to update any legacy entries in `accounts.enabled_sources`.
4. **`tests/test_scraper_factory_aliases.py`**:
   - Unit tests covering all variations and edge cases.
