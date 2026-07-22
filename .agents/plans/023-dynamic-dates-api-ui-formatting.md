# PLAN-023: Dynamiczne Formatowanie Dat Promptów w API Kont & Interfejsie UI

**Status:** IN_PROGRESS  
**Data dodania:** 2026-07-22  

---

## 🎯 Cel Projektowy
Automatyczna aktualizacja dat w promptach w zwracanych odpowiedziach z API (`GET /api/accounts`) oraz w interfejsie użytkownika (`app.js`) w formularzu edycji kampanii i w Piaskownicy AI.

---

## 🏗️ Specyfikacja Zmian

1. **Backend API (`src/main.py`)**:
   - Formatowanie `custom_prompt` przy zwracaniu kont w `GET /api/accounts`, `POST /api/accounts` i `PUT /api/accounts/{account_id}`.

2. **Frontend UI (`src/static/app.js`)**:
   - `formatPromptDates()` na poziomie JS przy ładowaniu promptu w formularzu edycji i Piaskownicy.
