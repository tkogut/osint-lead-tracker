# PLAN-068: Oczyszczenie listy źródeł OSINT w API i UI (Deduplikacja aliasów)

## Cel
Wyeliminowanie powielonych aliasów (`logintrade`, `bazakonkurenconosci`, `platformazakupowa`, `PlatformaZakupowa.pl` itp.) z listy źródeł w oknie wyboru kampanii w UI (`/api/sources`), przy jednoczesnym zachowaniu pełnej odporności silnika na aliasy w tle (`SCRAPER_REGISTRY` / `NORMALIZED_REGISTRY`).
Po wdrożeniu endpoint `/api/sources` zwraca dokładnie 8 unikalnych, czytelnie nazwanych źródeł z profesjonalnymi opisami.

## Zakres zmian

### 1. `src/scrapers/factory.py`
- Zdefiniowanie jawnego słownika kanonicznych wtyczek `CANONICAL_SCRAPERS`:
  - `Automatyka`: `AutomatykaScraper` (nazwa: "Automatyka.pl (Zapytania B2B)")
  - `BazaKonkurencyjnosci`: `BazaKonkurenconosciScraper` (nazwa: "Baza Konkurencyjności (BK2021 / Dotacje UE)")
  - `BiznesPolska`: `BiznesPolskaScraper` (nazwa: "Biznes-Polska (Przetargi i Inwestycje)")
  - `LoginTrade`: `LogintradeScraper` (nazwa: "LoginTrade (Przemysł i Spółki SP)")
  - `PlatformaZakupowa`: `PlatformaZakupowaScraper` (nazwa: "PlatformaZakupowa.pl (Gminy, PSZOK, Wodociągi)")
- Zachowanie `SCRAPER_REGISTRY` i `NORMALIZED_REGISTRY` bez zmian, aby utrzymać 100% tolerancji na aliasy przy wywołaniach `get_scraper_for_source()`.

### 2. `src/main.py`
- Aktualizacja endpointu `get_available_sources()` (`GET /api/sources`):
  - 3 źródła wbudowane:
    - `BZP` ("e-Zamówienia (BZP API)", opis biznesowy)
    - `Google` ("Wyszukiwarka Google (Grounding)", opis biznesowy)
    - `GUNB` ("Pozwolenia budowlane (GUNB RWDZ)", opis biznesowy)
  - 5 wtyczek skraperów z `CANONICAL_SCRAPERS` (z eleganckimi nazwami i opisami).
  - Usunięcie pętli iterującej po wszystkich roboczych kluczach `SCRAPER_REGISTRY.keys()`.

### 3. `tests/test_sources_cleanup.py`
- Test weryfikujący, że `GET /api/sources` zwraca dokładnie 8 unikalnych źródeł.
- Test weryfikujący brak jakichkolwiek duplikatów identyfikatorów lub aliasów wariantowych (`logintrade`, `bazakonkurenconosci`, `PlatformaZakupowa.pl`).
- Test weryfikujący, że funkcja `get_scraper_for_source()` nadal bezbłędnie rozwiązuje wszystkie aliasy.

## Role & Handshake
- Builder: Implementacja w `src/scrapers/factory.py`, `src/main.py` i testów w `tests/test_sources_cleanup.py`, wygenerowanie handshake Buildera.
- Auditor: Audyt jakościowy i testy (`pytest`), wygenerowanie handshake Auditora.
- Coordinator: Push do `main` przez `smart_commit.sh` -> automatyczne wdrożenie na VPS.
