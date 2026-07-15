# PLAN-009: Phase 5 — Wersjonowanie Promptów + Pętla Zwrotna CRM + Status Leadów

## 🎯 Cele Projektowe
Wdrożenie Fazy 5 systemu OSINT Lead Tracker:
1. **Prompt Versioning** — automatyczne wersjonowanie custom_prompt per kampania
2. **Status Leadów** — śledzenie statusu leada (new/in_progress/won/lost)
3. **Odoo Sync** — cykliczna synchronizacja statusów z Odoo CRM (scheduler 1x/dzień)
4. **Prompt Analytics** — endpoint KPI per wersja promptu + widok w UI

---

## 🏗️ Specyfikacja Architektury

### A. Baza Danych (SQLite / SQLAlchemy) — `src/models.py`

**Nowy Model `PromptVersion`:**
```python
id            INTEGER PK
account_id    FK -> Account
version       INTEGER  # rosnący numer wersji per konto
prompt_text   TEXT     # pełna treść instrukcji
created_at    DATETIME
```

**Aktualizacja Modelu `Lead`:**
- Dodanie kolumny: `status` VARCHAR(50) DEFAULT 'new'
- Dodanie kolumny: `prompt_version_id` FK -> PromptVersion (nullable)
- Dodanie kolumny: `last_synced_at` DATETIME (nullable)

### B. Migracja SQLite — `src/database.py`
- Dodanie wywołań `ALTER TABLE` w funkcji `init_db()` za pomocą `IF NOT EXISTS` (idempotentna migracja)
- Tworzenie tabeli `prompt_versions`

### C. Backend (FastAPI) — `src/main.py`

**Nowe endpointy:**
- `GET /api/analytics/prompts?account_id=<ID>` — zwraca listę wersji promptów z KPI:
  `version, created_at, total_leads, won_leads, lost_leads, in_progress_leads, conversion_rate`
- `POST /api/leads/sync` — ręczny trigger synchronizacji statusów z Odoo (sesja lub API token)
- `GET /api/leads` — rozszerzone o pole `status` w odpowiedzi

**Logika wersjonowania w `PUT /api/accounts/:id`:**
- Jeśli `custom_prompt` zmienił się względem aktualnej wersji → utwórz nową `PromptVersion`

**Scheduler cron (daily):**
- Dodanie zadania dziennej synchronizacji statusów leadów z Odoo (wywoływanego przez `sync_lead_statuses()`)

**Funkcja `sync_lead_statuses()`:**
- Pobiera leady z `odoo_id IS NOT NULL AND status NOT IN ('won','lost')`
- Dla każdego leada odpytuje Odoo XML-RPC (`probability`, `active`)
- Klasyfikacja statusu:
  - `probability == 100` → `won`
  - `active == False AND probability == 0` → `lost`
  - `active == True AND probability > 0` → `in_progress`
- Aktualizuje `lead.status` i `lead.last_synced_at`

### D. Powiązanie leadów z wersją promptu — `src/main.py` → `run_osint_pipeline()`
- Przed uruchomieniem wyszukiwania pobierz aktualny `PromptVersion.id` dla danego konta
- Przekaż `prompt_version_id` do funkcji `save_lead()`

### E. Frontend (HTML + JS + CSS) — `src/static/`

**W zakładce Kampanie / Konta → modal edycji:**
- Nowa sekcja "📊 Historia wersji promptów"
- Lista wersji: `v1 | 2026-07-10 | 5 leadów | 2 wygranych (40%)`
- Przycisk "Przywróć" → zapisuje wersję jako nowy prompt

**W widoku leadów (jeśli istnieje tabela):**
- Dodanie kolumny `Status` z badge: `new`/`in_progress`/`won`/`lost` w odpowiednich kolorach

---

## 🔑 Handshake Protocol (`.agents/swarm/`)

Każdy subagent MUSI zapisać plik handshake do `.agents/swarm/` przed zakończeniem:
- Builder: `<conversation_id>_builder_handshake.json`
- Auditor: `<conversation_id>_auditor_handshake.json`

Format:
```json
{
  "conversation_id": "...",
  "role": "Builder|Auditor",
  "status": "SUCCESS|FAIL",
  "files_modified": [...],
  "math_consistency_check": "PASSED|FAILED",
  "timestamp": "..."
}
```

---

## 🛠️ Podział Ról (Swarm Triad)

| Rola | Agent | Zadanie |
|------|-------|---------|
| **Coordinator** | Main thread (Ten agent) | Plan, Orchestracja, VPS deploy, git push |
| **Builder** | Subagent (branch: feature/phase5) | Implementacja models.py, database.py, main.py, static/ |
| **Auditor** | Subagent | Code review, math-consistency, handshake weryfikacja |

---

## ✅ Definicja Ukończenia (DoD)

- [x] Migracja DB działa idempotentnie (init_db) — try/except duplicate column
- [x] PromptVersion tworzony przy każdej zmianie custom_prompt — PUT /api/accounts/{id}
- [x] Lead.status aktualizowany przez sync z Odoo — sync_lead_statuses() + cron 07:00
- [x] Endpoint /api/analytics/prompts zwraca poprawne KPI — case() fix dla SQLite
- [x] UI wyświetla historię promptów w modalu kampanii — loadPromptVersionHistory()
- [x] Handshake Builder zapisany w `.agents/swarm/` — ecf5ed62_builder_handshake.json
- [x] Handshake Auditor zapisany w `.agents/swarm/` — 75929465_auditor_handshake.json (FAIL → bugs naprawione przez Coordinator)
- [x] Commit na main + deploy VPS — `b1b6ff1` pushed, container Started
- [x] Handshake Verified + Math-Consistency PASSED
