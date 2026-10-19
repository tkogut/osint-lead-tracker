# PLAN-067: Kampania "Tensometria i Podzespoły Wagowe" (EW + WP) oraz obsługa stron zbiorczych Automatyka.pl

## Cel
Wdrożenie nowej dedykowanej kampanii OSINT **"Tensometria i Podzespoły Wagowe"** (dla zespołu sprzedaży Elektronika Wagowa + Wagi Przemysłowe / Zbiornikowe - EW + WP), z kompletem 55+ branżowych słów kluczowych, 16 kodów CPV, wszystkimi źródłami poza GUNB (`["BZP", "Google", "Automatyka", "BazaKonkurencyjnosci", "BiznesPolska", "LoginTrade", "PlatformaZakupowa"]`) oraz zaawansowanym 5-filarowym promptem systemowym.
Dodatkowo: usprawnienie skrapera `AutomatykaScraper` w celu inteligentnej obsługi podstron zbiorczych marek i kategorii (`-27?topId=...`), tak aby zapytania o tensometry (np. Zemic nr 1028693) były precyzyjnie ekstrahowane z właściwym tytułem `<h2>` i datą publikacji.

## Zakres zmian

### 1. `src/seed.py`
- Zdefiniowanie modułowych stałych:
  - `TENSOMETRY_CPVS`: 16 kodów CPV (wagi, części wag, aparatura pomiarowa, przetworniki elektryczne, czujniki, maszyny dozujące, oprogramowanie, serwis).
  - `TENSOMETRY_KEYWORDS`: 55+ branżowych słów kluczowych opartych o ofertę MIW Group (tensometria, Zemic/HBM/Vishay/Sensocar/Dini Argeo/Flintec, wagi zbiornikowe, moduły ważące, dozowanie, ScalesCloud).
  - `TENSOMETRY_PROMPT`: Zaawansowany prompt systemowy z 5 filarami branżowymi (Tensometria & Przetworniki, Elektronika Wagowa & Mierniki, Wagi Zbiornikowe & Silosy, Dozowanie & Naważanie, Oprogramowanie ScalesCloud).
- W `seed_data()`:
  - Wyszukanie konta o nazwie w `["Tensometria i Podzespoły Wagowe", "Tensometria", "Podzespoły Wagowe"]`.
  - Jeśli nie istnieje: utworzenie konta z `enabled_sources = ["BZP", "Google", "Automatyka", "BazaKonkurencyjnosci", "BiznesPolska", "LoginTrade", "PlatformaZakupowa"]`, rejestracja `PromptVersion(version=1)`.
  - Jeśli istnieje: aktualizacja parametrów, scalenie słów kluczowych i CPV, zachowanie/inkrementacja wersji promptu.

### 2. `src/scrapers/automatyka.py`
- Usprawnienie parsowania podstron zbiorczych marek (`-27`):
  - Gdy URL zawiera `topId=\d+` lub strona zawiera bloki `<div class="box-styles ...">`:
    - Wyszukanie dedykowanego bloku odpowiadającego danemu `topId` (lub pierwszego aktywnego).
    - Ekstrakcja właściwego tytułu ogłoszenia z `<h2>` (np. `Tensometry Zemic` zamiast ogólnego `Zemic - zapytania o markę`).
    - Ekstrakcja daty publikacji bezpośrednio z metadanych danego zapytania (`<small>Opublikowano: ...</small>`).
    - Wyizolowanie treści i terminu składania ofert właściwego zapytania.

### 3. `tests/test_tensometria_seed_and_scraper.py`
- Test jednostkowy weryfikujący tworzenie i aktualizację konta "Tensometria i Podzespoły Wagowe" w `src/seed.py`.
- Test jednostkowy weryfikujący poprawność ekstrakcji ogłoszenia z podstrony zbiorczej Automatyka.pl z parametrem `topId`.
- Test jednostkowy weryfikujący zgodność promptu z `format_prompt_dates()`.

## Role & Handshake
- Builder: Implementacja zmian w `src/seed.py`, `src/scrapers/automatyka.py`, testy w `tests/test_tensometria_seed_and_scraper.py`, wygenerowanie handshake Buildera.
- Auditor: Audyt jakościowy, bezpieczeństwa i integralności (`pytest`), wygenerowanie handshake Auditora.
- Coordinator: Push do `main` przez `smart_commit.sh` -> automatyczne wdrożenie na VPS przez GitHub Actions.
