# PLAN-011: Poprawka Przypisywania Pustych Pól w Odoo (False instead of None)

## 🎯 Cel Projektowy
Naprawienie problemu, w którym wyczyszczenie handlowca (`odoo_user_id = none`) w ustawieniach kampanii nie powoduje wyczyszczenia handlowca w Odoo. Zamiast tego Odoo przypisuje domyślnego handlowca (właściciela klucza API, czyli Tomasza Koguta), ponieważ pole `user_id` było całkowicie pomijane w słowniku `vals` wysyłanym przez XML-RPC.

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. Integracja Odoo (`src/odoo_integration.py`)
- Zmienimy logikę budowania słownika `vals` w metodzie `create_lead`:
  - Jeśli `user_id` jest przekazany jako `None` (lub `0`), przypiszemy `vals["user_id"] = False`. W XML-RPC Odoo wartość `False` jest interpretowana jako `null` (brak przypisania/unassigned).
  - Dotyczy to również innych opcjonalnych pól powiązanych (Many2one), takich jak `team_id` czy `source_id`, aby zapobiec ich niechcianemu dziedziczeniu/domyślnemu przypisywaniu przez Odoo.

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator** (Ten agent): Zarządzanie planem, merge i deploy na VPS.
- **Builder** (Subagent): Modyfikacja `src/odoo_integration.py` w izolowanym worktree.
- **Auditor** (Subagent): Przegląd kodu pod kątem zgodności typów XML-RPC Odoo.
