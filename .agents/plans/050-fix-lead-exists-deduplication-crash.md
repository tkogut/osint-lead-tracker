# Plan Wdrożenia: Naprawa błędu i crashu w deduplikacji leadów (PRD)

## Cel projektu
Naprawa krytycznego błędu `AttributeError: type object 'Lead' has no attribute 'account_id'`, który powoduje wysypanie się dziennego skanowania OSINT (Daily OSINT scan) na etapie sprawdzania unikalności leadów (`lead_exists` w `database.py`).

---

## Proposed Changes

### 1. Poprawka w [src/database.py](file:///home/tkogut/projects/osint-lead-tracker/src/database.py)
- Zmiana w funkcji `lead_exists`:
  Zamiast bezpośredniego odwoływania się do `Lead.account_id`, wdrożenie bezpiecznego złączenia (outerjoin) z tabelą `PromptVersion`, aby poprawnie odczytać `account_id` powiązane z danym leadem:
  ```python
  query = query.outerjoin(PromptVersion, Lead.prompt_version_id == PromptVersion.id).filter(
      (PromptVersion.account_id == account_id) | (Lead.prompt_version_id == None)
  )
  ```

### 2. Utworzenie testu jednostkowego
- Dodanie testów weryfikujących funkcję `lead_exists` (zarówno dla dopasowań URL, jak i tytułów) w celu zabezpieczenia przed regresją.
