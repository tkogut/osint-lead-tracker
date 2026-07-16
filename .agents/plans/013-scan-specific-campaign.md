# PLAN-013: Ręczne Skanowanie Wybranej Kampanii (Trigger Campaign Scan)

## 🎯 Cel Projektowy
Dodanie możliwości manualnego wyzwalania procesu wyszukiwania leadów (skanowania) dla pojedynczej, wybranej kampanii bezpośrednio z poziomu interfejsu użytkownika w zakładce "Kampanie / Konta". Zapobiegnie to konieczności skanowania wszystkich kampanii jednocześnie, oszczędzając tokeny API oraz czas.

---

## 🏗️ Specyfikacja Zmian

### 1. API Backend (`src/main.py`)
- Rozszerzenie definicji funkcji `run_osint_pipeline(account_id: Optional[int] = None)`:
  - Jeśli `account_id` jest przekazany, baza SQLite zostanie zapytana tylko o ten konkretny rekord kampanii (niezależnie od statusu `is_active`, co ułatwi też testowanie).
  - Jeśli `account_id` jest równy `None`, zachowanie pozostanie standardowe (skanowanie wszystkich aktywnych kampanii).
- Aktualizacja endpointu `POST /trigger-osint`:
  - Dodanie opcjonalnego parametru zapytania `account_id: Optional[int] = None`.
  - Przekazywanie tej wartości bezpośrednio do wywołania `run_osint_pipeline(account_id=account_id)`.

### 2. Frontend HTML & CSS (`src/static/index.html` lub style w JS)
- Wykorzystamy istniejące style przycisków `.btn-primary` oraz `.btn-secondary` wewnątrz kart kampanii.

### 3. Frontend JS (`src/static/app.js`)
- **Renderowanie kart kampanii (`renderAccounts`):**
  - Dodanie przycisku `<button class="btn-primary scan-acc-btn" data-id="${acc.id}"><i class="fa-solid fa-play"></i> Skanuj</button>` w sekcji `account-card-actions` każdej karty kampanii.
- **Obsługa akcji kliknięcia (`scanAccount`):**
  - Podpięcie event listenera pod przyciski `.scan-acc-btn`.
  - Po kliknięciu:
    - Zablokowanie przycisku i zmiana etykiety na animowany spinner.
    - Wyświetlenie komunikatu Toast o rozpoczęciu skanowania danej kampanii.
    - Wywołanie `POST /trigger-osint?account_id={id}` z poprawnym nagłówkiem tokenu autoryzacji.
    - Wyświetlenie końcowego Toasta z podsumowaniem (znalezione leady, nowe, wysłane do Odoo) i odświeżenie danych na Dashboardzie.

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator** (Ten agent): Definicja planu, merge i wdrożenie na VPS.
- **Builder** (Subagent): Modyfikacja plików `src/main.py` oraz `src/static/app.js` w worktree.
- **Auditor** (Subagent): Przegląd kodu, weryfikacja poprawności przekazywania parametru i obsługi błędów w JS.
