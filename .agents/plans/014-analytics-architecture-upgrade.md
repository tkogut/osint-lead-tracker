# PLAN-014: Nowa Architektura Analityczna Dashboardu (Circuit Breaker + Grounding Metrics + Token Economy + SQLite Queue)

**Status:** IN PROGRESS  
**Data:** 2026-07-16  
**Priorytet:** KRYTYCZNY — wchodzi do produkcji jako nowa baza metryk jakościowych

---

## 1. Kontekst Architektoniczny

Po grillowym przeglądzie decyzji strategicznych wdrażamy 4 zmiany architektoniczne wynikające z analizy luk:

| # | Decyzja | Problem który zamyka |
|---|---------|----------------------|
| D1 | Circuit Breaker w potoku Odoo | "Zatrucie CRM" przez halucynujący prompt |
| D2 | Grounding metrics (chunks, queries) | Czarna skrzynka Grounding — niemożliwość liczenia raw_notices |
| D3 | Token Economy logging (input/output tokens) | Ukryte koszty pustych przebiegów Groundingu |
| D4 | asyncio.Queue Single Writer do SQLite | Race condition + database is locked na snapshotach |

---

## 2. Zmiany w Bazie Danych

### A. Nowe kolumny w `research_logs` (idempotentna migracja)
```sql
ALTER TABLE research_logs ADD COLUMN grounding_chunks_count INTEGER DEFAULT 0;
ALTER TABLE research_logs ADD COLUMN grounding_queries_count INTEGER DEFAULT 0;
ALTER TABLE research_logs ADD COLUMN input_tokens INTEGER DEFAULT 0;
ALTER TABLE research_logs ADD COLUMN output_tokens INTEGER DEFAULT 0;
```

### B. Nowa tabela `run_performance_snapshots`
```sql
CREATE TABLE IF NOT EXISTS run_performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,               -- BZP / Google / GUNB
    run_date DATE NOT NULL,
    leads_generated INTEGER NOT NULL DEFAULT 0,
    grounding_chunks_count INTEGER NOT NULL DEFAULT 0,
    grounding_queries_count INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    api_errors INTEGER NOT NULL DEFAULT 0,
    circuit_breaker_triggered BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
);
```

### C. Nowy status w tabeli `leads`
```sql
ALTER TABLE leads ADD COLUMN pending_approval BOOLEAN DEFAULT 0;
```
Leady z tym flagiem nie trafiają do Odoo — czekają na ręczne zatwierdzenie w UI.

---

## 3. Circuit Breaker (src/main.py)

### Parametr konfiguracyjny
```python
MAX_LEADS_PER_RUN = int(get_db_setting_sync("MAX_LEADS_PER_RUN", "10"))
```

### Logika bezpiecznika
W `run_osint_pipeline` per account per source:
```python
if len(leads) > MAX_LEADS_PER_RUN:
    logger.warning("CIRCUIT BREAKER TRIGGERED: %d leads > limit %d", len(leads), MAX_LEADS_PER_RUN)
    # Zapisz do SQLite z pending_approval=True
    for lead in leads:
        await save_lead(lead, odoo_id=None, pending_approval=True, ...)
    # NIE wywołuj Odoo XML-RPC
    # Zaloguj zdarzenie jako circuit_breaker_triggered=True
    continue  # przejdź do następnego source
```

---

## 4. Grounding Metadata Extraction (src/osint_engine.py)

W metodzie `_search_google`, po `response = client.models.generate_content(...)`:
```python
# Wyciągnij metadane Grounding
grounding_chunks = 0
grounding_queries = 0
input_tokens = 0
output_tokens = 0

if hasattr(response, 'usage_metadata') and response.usage_metadata:
    input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
    output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

if hasattr(response, 'candidates') and response.candidates:
    candidate = response.candidates[0]
    gm = getattr(candidate, 'grounding_metadata', None)
    if gm:
        chunks = getattr(gm, 'grounding_chunks', []) or []
        grounding_chunks = len(chunks)
        queries = getattr(gm, 'web_search_queries', []) or []
        grounding_queries = len(queries)
```

Zwracaj te dane w tuple razem z leads: `return leads, 200, response_hash, grounding_chunks, grounding_queries, input_tokens, output_tokens`

Dla BZP i GUNB (brak Grounding) — zwracaj 0 dla wszystkich metryk tokenów/chunks.

---

## 5. asyncio.Queue Single Writer (src/main.py)

### Definicja kolejki
```python
_analytics_queue: asyncio.Queue = asyncio.Queue()
```

### Worker (singleton w lifespanie)
```python
async def _analytics_writer_worker():
    """Singleton writer — sekwencyjnie zapisuje snapshoty do SQLite."""
    while True:
        event = await _analytics_queue.get()
        if event is None:  # sygnał zatrzymania
            _analytics_queue.task_done()
            break
        try:
            async with AsyncSessionLocal() as session:
                session.add(event)
                await session.commit()
        except Exception as e:
            logger.error("Analytics writer error: %s", e)
        finally:
            _analytics_queue.task_done()
```

### Integracja w lifespanie
```python
writer_task = asyncio.create_task(_analytics_writer_worker())
# przy shutdown:
await _analytics_queue.put(None)
await writer_task
```

---

## 6. Nowe Endpointy API

### GET /api/analytics/dashboard?account_id=<ID>
Zwraca zagregowane KPI dla dashboardu:
```json
{
  "yield_total": 42,
  "yield_per_chunk": 0.38,
  "total_chunks_analyzed": 110,
  "total_queries_fired": 28,
  "input_tokens_7d": 450000,
  "output_tokens_7d": 12000,
  "cost_per_run_avg": 3.2,
  "api_errors_7d": 1,
  "circuit_breaker_events": 0,
  "pending_approval_count": 0
}
```

### GET /api/leads/pending
Zwraca listę leadów oczekujących na zatwierdzenie (pending_approval=True).

### POST /api/leads/{id}/approve
Zatwierdza lead — wysyła do Odoo XML-RPC i zmienia pending_approval=False.

---

## 7. Frontend (Dashboard UI)

### Nowe KPI Cards zastępujące stare
- **Yield Total** (liczba leadów): zastępuje "Wszystkie Leady"  
- **Yield per Chunk** (leady / chunks źródłowych): zastępuje "Wagi Samochodowe" (vanity metric)
- **Queries Fired** (liczba zapytań Grounding): zastępuje "Wysłane do Odoo" (można zobaczyć w Odoo tabeli)
- **Cost per Run 7d** (tokeny input + output w 7 dniach): nowa karta

### Sekcja "Oczekujące na zatwierdzenie"
Tabela z leadami pending_approval, przycisk "Zatwierdź" per lead.

---

## 8. Modele SQLAlchemy

### Dodaj do models.py
```python
class RunPerformanceSnapshot(Base):
    __tablename__ = "run_performance_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)
    run_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    leads_generated = Column(Integer, nullable=False, default=0)
    grounding_chunks_count = Column(Integer, nullable=False, default=0)
    grounding_queries_count = Column(Integer, nullable=False, default=0)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    api_errors = Column(Integer, nullable=False, default=0)
    circuit_breaker_triggered = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    account = relationship("Account")
```

### Dodaj do Lead
```python
pending_approval = Column(Boolean, nullable=False, default=False)
```

### Dodaj do ResearchLog
```python
grounding_chunks_count = Column(Integer, nullable=True, default=0)
grounding_queries_count = Column(Integer, nullable=True, default=0)
input_tokens = Column(Integer, nullable=True, default=0)
output_tokens = Column(Integer, nullable=True, default=0)
```

### Dodaj do Account
```python
snapshots = relationship("RunPerformanceSnapshot", back_populates="account", cascade="all, delete-orphan")
```

---

## 9. Podział Ról (Swarm Triad)

- **Coordinator** (ten agent): Plan, merge, wdrożenie VPS, task.md
- **Builder** (Subagent): Implementacja w worktree `feature/phase6-analytics-architecture`
- **Auditor** (Subagent): Weryfikacja circuit breakera, metadanych grounding, kolejki SQLite

---

## 10. Kolejność Implementacji Buildera

1. `src/models.py` — dodaj `RunPerformanceSnapshot`, `pending_approval` do Lead, nowe kolumny do ResearchLog
2. `src/database.py` — idempotentne migracje ALTER TABLE dla nowych kolumn  
3. `src/osint_engine.py` — grounding metadata extraction, nowe zwracane wartości w `_search_google`
4. `src/main.py` — Circuit Breaker w pipeline, asyncio.Queue writer, nowe API endpoints
5. `src/static/index.html` — nowe KPI cards, sekcja "Oczekujące"
6. `src/static/app.js` — fetch nowych endpointów, renderowanie pending leads, approve handler
