# Changelog
> **OSINT Lead Tracker**

Wszystkie istotne zmiany w projekcie osint-lead-tracker będą dokumentowane w tym pliku. Format jest oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/) i projekt jest zgodny z [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.6.1] - 2026-07-21

### Added
- **Konfigurowalne Źródła Wyszukiwania w Kampaniach (Faza 7 / PLAN-016)**:
  - Wdrożono możliwość wyboru aktywnych źródeł OSINT (BZP API, Pozwolenia budowlane GUNB RWDZ, Wyszukiwarka Google Grounding) per kampania z walidacją "Zero-Source" w API.
  - Dodano podpowiedzi kosztowe oraz dynamiczne ukrywanie/wykluczanie nieaktywnych źródeł z logów analitycznych.
  - Zwiększono domyślne okno skanowania z 3 do 7 dni roboczych z możliwością konfiguracji via `SEARCH_WINDOW_DAYS`.
- **Fixes & Improvements**:
  - Naprawiono odporność na parsowanie źródeł przy zapisie i odczycie w FastAPI i interfejsie JS.
  - Dodano automatyczną migrację/auto-seeding klucza `SEARCH_WINDOW_DAYS` (wartość domyślna: `7`) w tabeli `settings` bazy danych SQLite przy inicjalizacji serwera.

## [1.6.0] - 2026-07-16

### Added
- **Architektura Analityczna Dashboardu (Faza 6)**:
  - Wdrożono bezpiecznik **Circuit Breaker** (oparty na bazie danych limit `MAX_LEADS_PER_RUN`) zapobiegający zatruciu Odoo CRM przez anomalie lub halucynacje LLM. Leady przekraczające limit trafiają do kwarantanny (`pending_approval`).
  - Dodano asynchroniczną kolejkę zapisu `asyncio.Queue` z dedykowanym workerem (Single Writer) eliminującą błędy SQLite `database is locked`.
  - Wprowadzono precyzyjną analitykę zużycia tokenów Gemini (Input/Output Tokens) oraz metryk Google Grounding (`grounding_chunks`, `web_search_queries`), eliminując martwe wskaźniki (vanity metrics).
  - Wdrożono sekcję **Kwarantanny** w panelu UI Dashboard wraz z możliwością manualnego przeglądania, odrzucania oraz akceptacji leadów (z poprawnym pobieraniem mapowania multi-company danej kampanii i zabezpieczeniem przed utratą danych w CRM).
  - Dodano możliwość manualnego uruchamiania skanowania dla pojedynczej, wybranej kampanii bezpośrednio z kart w zakładce "Kampanie".

## [1.5.0] - 2026-07-15

### Added
- **Historia wersji i przywracanie promptów (Faza 5)**: Wdrożono tabelę `prompt_versions` rejestrującą zmiany w promptach systemowych per kampania. Z poziomu UI dodano listę wersji ze statystykami efektywności (konwersja %, wygrane/przegrane leady) oraz przycisk pozwalający przywrócić dowolną poprzednią wersję.
- **Synchronizacja statusów leadów z CRM**: Dodano background task `/api/leads/sync-crm` automatycznie odpytujący Odoo XML-RPC i aktualizujący statusy szans w lokalnej bazie SQLite (Won, Lost, Active %).
- **Filtrowanie i sortowanie leadów**: Wdrożono w interfejsie graficznym zaawansowane filtrowanie listy leadów po statusach CRM oraz sortowanie wyników.
- **Zaawansowane raporty i weryfikacja logów (Faza 3 Expansion)**: Dodano endpointy analityczne (`GET /api/analytics/kpis` i `/api/analytics/timeline`) agregujące liczbę skanów, znalezione namiary i błędy API na osi czasu.
- **Twarde dowody w logach**: Wprowadzono rejestrowanie skrótów SHA-256 surowych odpowiedzi z API oraz parametrów zapytania bezpośrednio w szczegółach logu w UI.
- **Weryfikacja Odoo Multicompany**: Wizualizacja w sekcji Accounts i w logach dokładnego mapowania Odoo (`company_id`, `user_id`, `tag_ids`, `team_id`, `source_id`).
- **Notification Gate**: System powiadomień i alertów w UI, natychmiast sygnalizujący awarie zewnętrznych API (błędy 4xx/5xx w logach) lub problemy z połączeniem z Odoo.
- **Zintegrowany Swarm Triad Handshake Gate**: Wdrożono skrypty `generate-handshake.py` i `validate-handshakes.py` weryfikujące poprawność wykonania zadań. Zmodyfikowano `smart_commit.sh` jako blokadę (Gate) uniemożliwiającą push dla roli Coordinator bez handshake'u od Buildera.
- **Obsługa zmiany hasła**: Wdrożono zmianę hasła administratora panelu z poziomu UI Settings.

### Changed
- **Dwukolumnowy układ modalu edycji**: Modal dodawania/edycji kampanii został podzielony na dwie przejrzyste kolumny — po lewej konfiguracja wyszukiwania i CRM, po prawej dynamiczny prompt systemowy z historią wersji.
- **Maskowanie poświadczeń (Secrets Redaction)**: Wdrożono automatyczne maskowanie i usuwanie surowych wartości kluczy API i haseł (np. `GEMINI_API_KEY`) z logów systemu i raportów przesyłanych do czatu dewelopera.

## [1.3.0] - 2026-07-14

### Changed
- **Klucz API zamiast hasła Odoo**: Zmieniono nazwę zmiennej środowiskowej z `ODOO_PASSWORD` na `ODOO_API_KEY` w konfiguracji ustawień i integracji XML-RPC, ułatwiając bezpieczne uwierzytelnianie tokenami (API Keys).

## [1.2.0] - 2026-07-13

### Added
- **Skaner pozwoleń budowlanych GUNB (RWDZ)**: Integracja z rejestrem wniosków, decyzji i zgłoszeń budowlanych GUNB w celu wykrywania prywatnych i komercyjnych budów wag samochodowych w 16 województwach.
- **Pamięć podręczna (Content-Length)**: System cache'owania sprawdzający wielkość plików ZIP przy użyciu zapytań `HEAD` – eliminuje to zbędne pobieranie setek megabajtów danych przy codziennych skanach.
- **Automatyczny parser CSV**: Autonomiczny, pamięciowo-wydajny parser CSV czytający dane strumieniowo prosto ze skompresowanych archiwów ZIP bez obciążania pamięci RAM serwera.

## [1.1.0] - 2026-07-13

### Added
- **Integracja z API e-Zamówień (BZP)**: Bezpośrednie odpytywanie rządowej bazy REST API dla kodów CPV związanych z technologią wagową (`42923110-6` - wagi samochodowe, `42923000-2`, `42923200-0`).
- **Lokalny pre-filter**: Optymalizacja tokenów i zapytań LLM poprzez wstępne przeszukiwanie słów kluczowych (np. `waga`, `ważenie`) w pobranym z API kodzie HTML ogłoszenia przed wysłaniem do Gemini.
- **Weryfikacja kontekstowa**: Wykorzystanie modelu Gemini 2.5 Flash do dokładnej ekstrakcji parametrów i weryfikacji, czy ogłoszenia z Generalnego Rejestru e-Zamówień dotyczą wag dla pojazdów ciężarowych.

### Changed
- **Podejście Hybrydowe**: Przebudowa silnika wyszukiwania na model hybrydowy (BZP API dla 100% wykrywalności zamówień publicznych + Google Search Grounding dla zleceń komercyjnych i prywatnych).
- **Zakres Czasowy**: Zmiana domyślnego okna skanowania z ostatnich 24 godzin na **ostatnie 3 dni robocze**.
- **Dynamiczne Liczenie Dat**: Automatyczne wyznaczanie granicy 3 dni roboczych w oparciu o kalendarz (pomijanie sobót i niedziel).
- **Format Typu Rekordu Odoo**: Zmiana typu nowo tworzonego rekordu w Odoo z `opportunity` (szansa) na `lead` (wstępny namiar) zgodnie ze specyfikacją CRM.
- **Opis HTML w Odoo**: Wdrożenie generowania estetycznych i przejrzystych tabel HTML bezpośrednio na karcie leada w Odoo CRM (lepsza czytelność parametrów, lokalizacji i priorytetu).

### Fixed
- **Kodowanie URL e-Zamówień**: Dodano parametr `safe=""` do funkcji `urllib.parse.quote`, co zmusiło parser do kodowania ukośników jako `%2F`, naprawiając niedziałające linki szczegółów ogłoszeń.
- **Obsługa pustych odpowiedzi AI**: Dodano zabezpieczenie w parserze `_parse_leads()`, zapobiegające rejestrowaniu błędów `JSONDecodeError` przy pustej odpowiedzi z modelu Gemini.
- **Prawa dostępu SQLite (Docker)**: Naprawiono problem z uprawnieniami zapisu do bazy leads.db z wnętrza kontenera działającego jako użytkownik nieuprzywilejowany (`appuser`: 1001) na wolumenie hosta VPS.
