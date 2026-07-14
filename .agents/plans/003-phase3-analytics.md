# PLAN-003: Zaawansowana Analityka, Raporty i Wizualizacja w UI (Faza 3)

## 🎯 Cele Biznesowe
Dostarczenie administratorom pełnego wglądu w metryki efektywności silnika (współczynnik sukcesu, awarie API), przejrzystego audytu matematycznych dowodów (SHA-256) oraz wczesnego ostrzegania w przypadku błędów autoryzacji Odoo lub przerw w działaniu portali rządowych (BZP/GUNB).

---

## 🏗️ Specyfikacja Techniczna i Modyfikacje Kodu

### 1. Backend (FastAPI Endpoints)
Dodanie routera `/api/analytics` w `src/main.py`:
* `GET /api/analytics/kpis`: Zwraca zagregowane dane:
  * Suma wykonanych skanów (`ResearchLog`).
  * Współczynnik sukcesu (procent logów ze statusem `200`).
  * Liczba awarii (statusy `!= 200` lub błędy).
  * Całkowita liczba wykrytych ofert oraz zapisanych w CRM.
* `GET /api/analytics/timeline`: Zwraca wolumen skanów i znalezionych leadów na osi czasu (pogrupowane po dniach) do wizualizacji trendów.

### 2. Frontend (HTML, CSS, JS)
* **Wizualizacja KPI**: Dodanie nowych wykresów lub kafelków trendów na Dashboardzie prezentujących status połączenia i skuteczność LLM.
* **Zaawansowany Panel Logów**:
  * Dodanie filtrów: Kampania, Status (Sukces/Błąd), Źródło (BZP/Google/GUNB) oraz zakres dat.
  * Interaktywny podgląd logu: Kliknięcie w log otwiera szczegółowy podgląd JSON zawierający parametry `query_params`, pełny hash SHA-256 oraz powiązane metadane Odoo.
* **Notification Gate (Status Systemowy)**:
  * Stały element u góry ekranu (np. przycisk statusu "System OK" / "Awarie wykryte").
  * Jeśli w ostatnich 5 logach wystąpił status `!= 200`, wyświetlamy widoczny czerwony alert ostrzegający o problemach z Odoo lub API rządowymi.
* **Wizualizacja Multicompany**:
  * Na kafelkach kampanii w zakładce "Konta" oraz w podglądzie logów wyświetlamy przypisane mapowanie: Spółka Odoo (`company_id`), Handlowiec (`user_id`) i Tagi (`tag_ids`).

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator** (Ja): Zarządzanie backlogiem (`task.md`), planami (`003-phase3-analytics.md`), mergowaniem i wdrożeniem VPS.
* **Builder** (Subagent `cavecrew-builder` lub dedykowany): Implementacja backendu w `src/main.py` oraz frontendu w `src/static/`.
* **Auditor** (Subagent `cavecrew-reviewer`): Weryfikacja kodu przed scaleniem, sprawdzenie spójności modeli i poprawności JavaScriptu.
