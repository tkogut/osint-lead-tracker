# Plan Wdrożenia: Dynamiczna lista i kontrola dostępnych modeli Gemini (PRD)

## Cel projektu
Wdrożenie mechanizmu dynamicznego pobierania dostępnych modeli z API Google Gemini, aby zapobiec wybieraniu przestarzałych lub nieobsługiwanych modeli (np. `gemini-2.5-flash-lite` lub innych wycofanych wersji) w ustawieniach kampanii.

---

## Proposed Changes

### 1. Nowy endpoint w backendzie
#### `GET /api/available-models` w [src/main.py](file:///home/tkogut/projects/osint-lead-tracker/src/main.py)
- Pomiary i pobranie klucza `GEMINI_API_KEY` z bazy danych lub konfiguracji.
- Wywołanie `client.models.list()` z biblioteki `google-genai` w celu pobrania aktualnej listy modeli oferowanych przez API Google.
- Przefiltrowanie listy modeli (wybór modeli tekstowych/generatywnych zawierających frazę `"gemini"` w nazwie).
- Oczyszczenie nazw z prefiksów (np. mapowanie `models/gemini-2.5-flash` na `gemini-2.5-flash`).
- Zwrócenie listy jako JSON:
  ```json
  ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
  ```
- Obsługa błędów (np. brak klucza API, brak połączenia): w przypadku błędu zwracamy predefiniowaną listę bezpiecznych, sprawdzonych modeli (fallback).

### 2. Uaktualnienie frontendu
#### Modyfikacja [src/static/index.html](file:///home/tkogut/projects/osint-lead-tracker/src/static/index.html) oraz [src/static/app.js](file:///home/tkogut/projects/osint-lead-tracker/src/static/app.js)
- Zastąpienie zahardkodowanych opcji `<option>` w selektorach modeli na dynamicznie generowane listy.
- Pobieranie listy modeli przy starcie panelu administracyjnego z `/api/available-models`.
- Dynamiczne renderowanie elementów w formularzu edycji/tworzenia kampanii (np. `#account-model` / `#campaign-model`).
