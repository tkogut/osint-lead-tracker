# PLAN-022: Dynamiczne Daty w Promptach Kampanii & Rozszerzenie Scrapera Logintrade

**Status:** COMPLETED / DONE  
**Data realizacji:** 2026-07-22  


---

## 🎯 Cel Projektowy
Naprawa błędu zwracania `{"leady": []}` z powodu starych sztywnych dat w promptach kampanii oraz rozszerzenie wsparcia subdomen Logintrade (`*.logintrade.net`, `/zapytania_email,...`).

---

## 🏗️ Specyfikacja Zmian

1. **Silnik AI & Piaskownica (`src/main.py`, `src/osint_engine.py`)**:
   - Dynamiczna automatyczna podmieniana nagłówka daty w prompcie przed wywołaniem Gemini na aktualną datę systemową (`today_str` i `start_str`).

2. **Scraper Logintrade (`src/scrapers/logintrade.py`)**:
   - Wzorce regex wspierające `/zapytania_email,...` i subdomeny firmowe.
