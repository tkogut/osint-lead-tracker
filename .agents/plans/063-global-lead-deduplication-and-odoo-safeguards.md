# PLAN-063: Global Lead Deduplication & Odoo Safeguards

## Cel
Wyeliminowanie problemu duplikowania leadów w Odoo i bazie SQLite (przypadek GWDA z 08.10 i 10.10):
1. Różne adresy URL i tytuły z różnych portali (np. BiznesPolska vs e-Zamówienia/BZP z adresem inwestora).
2. Ominięcie sprawdzania duplikatów przy przypisaniu do innego konta/kampanii w `lead_exists`.
3. Tworzenie rekordu w Odoo PRZED udanym zapisem w bazie SQLite, co powodowało tworzenie osieroconych duplikatów w CRM w razie `IntegrityError`.
4. Brak pre-checku duplikatów w Odoo przed wykonaniem `create_lead`.

## Zakres zmian
1. **`src/database.py`**:
   - `is_title_duplicate`: dodanie analizy zawierania tokenów (overlap coefficient / containment >= 0.80) dla tytułów różniących się dodanym adresem inwestora lub dopiskiem. Obniżenie progu Jaccard z 0.85 do 0.70.
   - `lead_exists`:
     - Globalne sprawdzenie `Lead.url` bez filtrowania po `account_id` (ponieważ tabela `leads` ma globalny `UNIQUE(url)`).
     - Ekstrakcja numeru ogłoszenia BZP z URL (np. `00478926`) i deduplikacja na poziomie numeru postępowania.
   - `update_lead_odoo_id`: asynchroniczna funkcja do aktualizacji `odoo_id` w rekordzie `Lead`.
2. **`src/odoo_integration.py`**:
   - W `OdooClient.create_lead`: sprawdzenie przez `search` w Odoo, czy w `crm.lead` (pole `description`) istnieje już rekord z tym samym URL. Jeśli tak — zwrot istniejącego ID bez tworzenia duplikatu.
3. **`src/main.py`**:
   - Odwrócenie kolejności zapisu: najpierw zapis w SQLite (`save_lead`), a dopiero po sukcesie (brak `IntegrityError`) wywołanie `odoo.create_lead` i aktualizacja `odoo_id` przez `update_lead_odoo_id`.
4. **`tests/test_deduplication.py`**:
   - Testy jednostkowe:
     - Deduplikacja tytułów z zawieraniem (przypadek GWDA / dopisany adres).
     - Globalna deduplikacja URL między różnymi kontami.
     - Deduplikacja po numerze BZP w URL.
     - Spójność `update_lead_odoo_id`.

## Role & Handshake
- Builder: Implementacja zmian i testów, handshake.
- Auditor: Audyt i weryfikacja testów, handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> automatyczny deploy na VPS.
