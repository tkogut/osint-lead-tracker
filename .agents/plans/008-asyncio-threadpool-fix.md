# PLAN-008: Uwolnienie Pętli Zdarzeń (Event Loop) podczas wyszukiwania OSINT

## 🎯 Cele Projektowe
Zapobieganie blokowaniu serwera (brak odpowiedzi na inne zapytania HTTP) podczas długotrwałego wyszukiwania OSINT (wielo-kampanijnego).

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. Backend (FastAPI - `src/main.py`)
* Import `asyncio` na początku pliku.
* Modyfikacja funkcji `run_osint_pipeline`:
  * Oddelegowanie synchronicznej, blokującej metody `engine.run_search_for_account(account)` do osobnego wątku za pomocą `await asyncio.to_thread(...)`.
  * Oddelegowanie synchronicznego wywołania XML-RPC Odoo `odoo.create_lead(...)` do osobnego wątku za pomocą `await asyncio.to_thread(...)`.
* Dzięki temu główna pętla zdarzeń FastAPI (Event Loop) pozostanie całkowicie wolna, co pozwoli serwerowi na równoległe obsługiwanie innych zapytań użytkowników (np. pobieranie logów, podgląd dashboardu) w trakcie trwania skanowania.

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator**: Zarządzanie planem i wdrożeniem.
* **Builder**: Wprowadzenie `asyncio.to_thread` w `src/main.py`.
* **Auditor**: Testy obciążeniowe i weryfikacja responsywności API podczas skanowania.
