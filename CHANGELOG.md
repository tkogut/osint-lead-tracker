# Changelog
> **OSINT Lead Tracker**

Wszystkie istotne zmiany w projekcie osint-lead-tracker będą dokumentowane w tym pliku. Format jest oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/) i projekt jest zgodny z [SemVer](https://semver.org/spec/v2.0.0.html).

---

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
