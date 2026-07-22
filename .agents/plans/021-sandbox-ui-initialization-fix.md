# PLAN-021: Poprawa Inicjalizacji Sandboxa i Obsługa Wyboru Kampanii oraz Źródeł w UI

**Status:** COMPLETED / DONE  
**Data realizacji:** 2026-07-22  


---

## 🎯 Cel Projektowy
Naprawa błędu braku możliwości wyboru kampanii oraz źródła w Piaskownicy AI poprzez prawidłowe wywołanie `loadSandboxData()` przy przełączaniu zakładek w `src/static/app.js`.

---

## 🏗️ Specyfikacja Zmian

1. **Frontend UI (`src/static/app.js`)**:
   - Dodanie `loadSandboxData()` pobierającej `/api/accounts` i `/api/sources`.
   - Dopisanie `if (targetTab === "sandbox") loadSandboxData()` do handlera zakładek.
   - Wywołanie `loadSandboxData()` przy starcie aplikacji.
