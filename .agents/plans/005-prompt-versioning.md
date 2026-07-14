# PLAN-005: Wersjonowanie Promptów i Pętla Zwrotna CRM (Faza 4)

## 🎯 Cele Projektowe
Wdrożenie mechanizmu śledzenia zmian w promptach systemowych (Prompt Versioning) oraz integracja zwrotna z Odoo CRM w celu automatycznego wyliczania konwersji i skuteczności każdego promptu (Prompt Performance Analytics).

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. Baza Danych (SQLite / SQLAlchemy)
* **Nowy Model `PromptVersion`**:
  * `id` (PK)
  * `account_id` (FK -> `Account`)
  * `version` (INT, rosnący numer wersji dla danej kampanii)
  * `prompt_text` (TEXT, instrukcja systemowa)
  * `created_at` (DATETIME)
* **Aktualizacja Modelu `Lead`**:
  * `prompt_version_id` (FK -> `PromptVersion`, powiązanie z wersją promptu, która wygenerowała leada)
  * `status` (VARCHAR, dopuszczalne stany: `'new'`, `'in_progress'`, `'won'`, `'lost'`)
  * `last_synced_at` (DATETIME, data ostatniej synchronizacji z Odoo)

### 2. Backend (FastAPI + Odoo Client)
* **Pętla synchronizacji statusów (`/api/leads/sync`)**:
  * Asynchroniczne zadanie wywoływane przez Schedulera (np. co godzinę lub raz na dobę).
  * Odpytanie bazy o leady z `status` różnym od `'won'` i `'lost'` posiadające przypisany `odoo_id`.
  * Pobranie statusów szans z Odoo przy użyciu XML-RPC (`fields=['active', 'probability']`).
  * Klasyfikacja statusu (Opcja A):
    * Jeśli `probability == 100` -> `'won'` (sukces)
    * Jeśli `active == False` i `probability == 0` -> `'lost'` (odrzucony)
    * Jeśli `active == True` i `probability > 0` i `probability < 100` -> `'in_progress'`
* **Endpoint KPI i Rankingu**:
  * `GET /api/analytics/prompts?account_id=<ID>`: zwraca listę wersji promptów dla konta wraz ze statystykami:
    * `version`, `created_at`, `total_leads`, `won_leads`, `lost_leads`, `conversion_rate` (procent won_leads).

### 3. Interfejs Użytkownika (UI)
* **Podgląd Historii Promptów**:
  * W oknie edycji kampanii (prawy panel) dodana zostanie sekcja/zakładka "Historia wersji".
  * Wyświetlenie listy historycznych promptów wraz ze wskaźnikami skuteczności (% konwersji).
  * Przycisk "Przywróć tę wersję" (nadpisuje obecny prompt wybraną instrukcją historyczną i tworzy nową wersję w bazie).

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator** (Ja): Zarządzanie planem, backlogiem i VPS.
* **Builder** (Subagent): Implementacja schematów DB, endpointów FastAPI oraz formularzy UI.
* **Auditor** (Subagent): Przegląd kodu, test spójności relacji i walidacji XML-RPC Odoo.
