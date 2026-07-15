# PLAN-010: Przywracanie Promptów oraz Filtrowanie i Sortowanie Leadów (TSK-021, TSK-022)

## 🎯 Cele Biznesowe i Projektowe
Umożliwienie użytkownikowi:
1. Szybkiego przywrócenia dowolnego historycznego promptu z poziomu listy wersji (TSK-021) z automatycznym zapisem jako nowa wersja.
2. Wygodnego wyszukiwania, filtrowania po statusie (Nowy, W toku, Wygrany, Przegrany) oraz sortowania (po dacie, po priorytecie) na liście leadów na Dashboardzie (TSK-022).

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. API Backend (FastAPI) — `src/main.py`
- W endpoincie `GET /api/analytics/prompts` dodamy klucz `"prompt_text": pv.prompt_text` do zwracanego słownika każdej wersji, aby frontend miał pełną treść promptu bez konieczności dodatkowego zapytania.

### 2. Frontend HTML — `src/static/index.html`
- W sekcji tabeli leadów (linia 187-190) dodamy kontrolki:
  - `<select id="lead-filter-status">` z opcjami: `Wszystkie statusy`, `Nowy (new)`, `W toku (in_progress)`, `Wygrany (won)`, `Przegrany (lost)`.
  - `<select id="lead-sort">` z opcjami: `Najnowsze najpierw`, `Najstarsze najpierw`, `Priorytet (Wysoki → Niski)`.

### 3. Frontend JS — `src/static/app.js`
- **Przywracanie wersji promptu (TSK-021):**
  - W funkcji `loadPromptVersionHistory` dodamy przycisk `"Przywróć"` do każdego elementu wersji.
  - Kliknięcie przycisku wstawi pełną treść promptu do pola tekstowego `#acc-prompt` w modalu i wyświetli komunikat o załadowaniu promptu. Następnie po kliknięciu "Zapisz" przez użytkownika, zostanie wysłany standardowy `PUT /api/accounts/:id`, który automatycznie utworzy kolejną wersję w bazie danych (ponieważ treść uległa zmianie względem aktualnej).
  
- **Filtrowanie i Sortowanie Leadów (TSK-022):**
  - Zapiszemy pobraną listę leadów z `/api/leads` w zmiennej globalnej `allLeads` w pliku JS.
  - Podepniemy event listenery (`input` / `change`) pod kontrolki `#lead-search`, `#lead-filter-status` i `#lead-sort`.
  - Stworzymy funkcję pomocniczą `filterAndRenderLeads()`, która na podstawie wartości z powyższych kontrolek przefiltruje `allLeads` i wywoła `renderLeads(filteredLeads)`.

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator** (Ten agent): Definicja planu, orkiestracja, commit i wdrożenie na VPS.
- **Builder** (Subagent): Modyfikacja plików backendu i frontendu w worktree `feature/phase5-tsk021-022`.
- **Auditor** (Subagent): Przegląd kodu, test spójności filtrów i poprawności przywracania wersji.
