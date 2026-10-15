# Execution Plan: Scraper Source Name Aliases & Normalization

## Goal
Eliminate 404 scan errors caused by casing variations, domain suffixes, or typos in scraper source names (e.g. `LoginTrade` vs `Logintrade`, `BazaKonkurencyjnosci` vs `BazaKonkurenconosci`), ensuring every configured source resolves reliably. Fixes #5.

## Scope
- `src/scrapers/factory.py`: Add `normalize_source_name` and expand `SCRAPER_REGISTRY` with canonical mappings and fallback resolution.
- `src/osint_engine.py`: Normalize source strings in scan dispatch (`scan_all_sources`), covering built-in sources (`BZP`, `Google`, `GUNB`) and plugin scrapers.
- `src/main.py` & `src/seed.py`: Normalize source strings on account save/load and seed. Add idempotent migration for existing accounts.
- `tests/test_scraper_factory_aliases.py`: Comprehensive test coverage.

## Risks
- Low risk: changes are isolated to name normalization and resolution fallbacks. Existing exact-match dictionary keys remain intact for backward compatibility.

## Implementation Plan

### Phase 1: Normalization & Factory Aliases
- Step 1.1: Implement `normalize_source_name(name: str) -> str` in `src/scrapers/factory.py` handling whitespace, case, domain endings, punctuation.
- Step 1.2: Register common aliases in `SCRAPER_REGISTRY` and update `get_scraper_for_source` with normalized fallback resolution.

### Phase 2: Engine & Account Dispatch Resilience
- Step 2.1: Normalize source dispatching in `src/osint_engine.py` (`scan_all_sources` / `_search_plugin`) so built-in and plugin sources are case- and alias-resilient.
- Step 2.2: Ensure `src/main.py` normalizes `enabled_sources` and performs idempotent startup migration on SQLite accounts table.

### Phase 3: Testing & Validation
- Step 3.1: Create `tests/test_scraper_factory_aliases.py` testing all variations, casing, typos, and negative cases.
- Step 3.2: Run full validation gate and audit.

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Normalization & Factory Aliases

- [x] 1.1 Implement normalize_source_name and register aliases
- [x] 1.2 Implement fallback resolution in get_scraper_for_source

### Phase 2: Engine & Account Dispatch Resilience

- [x] 2.1 Update osint_engine source dispatching
- [x] 2.2 Update main.py source parsing and seed migration

### Phase 3: Testing & Validation

- [x] 3.1 Add comprehensive test suite in tests/test_scraper_factory_aliases.py
- [x] 3.2 Run full validation gate and audit
