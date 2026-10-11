# PLAN-059: Railway Scales (Wagi Kolejowe) Prompt Update & CPV Expansion

## Cel
Wdrożenie dedykowanego promptu systemowego OSINT dla kampanii "Wagi Kolejowe" oraz rozszerzenie kodów CPV o infrastrukturę torową, aparaturę kolejową, wagi dynamiczne (WIM) i serwisy/legalizacje.
Zgodnie z dyspozycją użytkownika:
- Zastosować nowy prompt systemowy dla wag kolejowych (Filar 1: wagi statyczne i dynamiczne, Filar 2: modernizacje bocznic, zakaz redirectów, reguły dat).
- NIE zmieniać istniejących słów kluczowych konta (jeśli konto już istnieje, zachować jego obecne `target_keywords`).
- Sprawdzić listę CPV i dodać brakujące kody do `target_cpvs` (zarówno w seed.py, jak i w bazie danych).

## Lista kodów CPV (`RAILWAY_CPVS`):
- `42923110-6` – Wagi pomostowe
- `42923000-2` – Wagi i urządzenia do ważenia
- `42923200-0` – Urządzenia do ważenia o stałej masie i wagi samoczynne (wagi dynamiczne WIM)
- `42923100-3` – Aparatura wagowa
- `45234100-7` – Roboty budowlane w zakresie budowy linii kolejowych (bocznice kolejowe)
- `45234116-2` – Roboty w zakresie torów kolejowych
- `50433000-9` – Usługi w zakresie napraw i konserwacji urządzeń do ważenia (legalizacje i serwisy)
- `38540000-2` – Maszyny i aparatura badawcza i pomiarowa
- `34940000-8` – Aparatura kolejowa
- `34946120-7` – Urządzenia torowe

## Zakres zmian
1. **`src/seed.py`**:
   - Zdefiniowanie `RAILWAY_PROMPT` i `RAILWAY_CPVS`.
   - W `seed_data()`: obsługa tworzenia i aktualizacji konta `"Wagi Kolejowe"`.
   - Jeśli konto istnieje: aktualizacja `custom_prompt = RAILWAY_PROMPT`, scalenie CPV (dodanie brakujących bez usuwania istniejących), zachowanie istniejących `target_keywords`.
   - Jeśli konto nie istnieje: utworzenie konta `"Wagi Kolejowe"` z pełną konfiguracją.
2. **`tests/test_railway_seed.py`**:
   - Test jednostkowy weryfikujący poprawne utworzenie/aktualizację konta "Wagi Kolejowe", zachowanie słów kluczowych i scalenie kodów CPV.

## Role & Handshake
- Builder: Implementacja w `src/seed.py`, testy w `tests/test_railway_seed.py`, handshake.
- Auditor: Audyt i testy (`pytest`), handshake.
- Coordinator: Push do `main` via `smart_commit.sh` -> automatyczny deploy na VPS.
