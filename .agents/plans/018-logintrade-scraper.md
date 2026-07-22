# PLAN-018: Dedykowany Scraper logintrade.pl (Wtyczka OSINT Plugin)

**Status:** IN_PROGRESS  
**Data dodania:** 2026-07-22  

---

## 🎯 Cel Projektowy
Stworzenie nowej wtyczki skrapera dla platformy przetargowej `logintrade.pl` (Logintrade Zapytania Ofertowe i Przetargi).
Skraper powiększy zasób bezpłatnych źródeł OSINT dla kampanii B2B (np. wagi samochodowe, automatyka, aparatura), pozyskując zlecenia z platform przetargowych grup zakupowych oraz przedsiębiorstw komercyjnych korzystających z systemu Logintrade.

---

## 🏗️ Specyfikacja Zmian

1. **Wtyczka Scrapera (`src/scrapers/logintrade.py`)**:
   - Klasa `LogintradeScraper(BaseScraper)`.
   - Pobieranie ogłoszeń z `https://logintrade.pl/zapytania-ofertowe`.
   - TLS Impersonate z `curl_cffi` (Chrome 124).
   - Deduplikacja Tier 0 z `is_url_visited` i `mark_url_visited`.
   - Czyszczenie DOM (`DOMSanitizer`) oraz pre-filter słów kluczowych.

2. **Rejestracja w Fabryce (`src/scrapers/factory.py` & `src/scrapers/__init__.py`)**:
   - Dodanie `"Logintrade": LogintradeScraper` do `SCRAPER_REGISTRY`.

3. **Dokumentacja i Backlog (`task.md` & `CHANGELOG.md`)**.
