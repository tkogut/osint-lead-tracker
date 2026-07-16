# PLAN-012: Poprawka Obsługi Kampanii Niestandardowych (AI Prompt & JSON Parsing Fix)

## 🎯 Cele Projektowe
Umożliwienie poprawnego działania innych kampanii niż "Wagi Samochodowe" (tj. Wagi Przemysłowe, Wzorcowania, Agro):
1. **Dynamiczny Prompt BZP:** Zastąpienie twardo zakodowanego filtra "wagi samochodowej" w `_verify_bzp_notice` ogólnym sprawdzeniem zgodności z kryteriami `custom_prompt` danej kampanii (jeśli jest ustawiony).
2. **Elastyczny Parser JSON (SQLite):** Mapowanie synonimów pól JSON generowanych przez różne wersje promptów (np. `tytul_generowany` -> `tytul`, `nazwa_inwestora` -> `inwestor`, `opis_szczegolowy` -> `zakres`) podczas zapisu do SQLite.

---

## 🏗️ Specyfikacja Zmian

### 1. Backend: Walidacja BZP (`src/osint_engine.py` -> `_verify_bzp_notice`)
- Jeśli `account` posiada `custom_prompt`, wygenerujemy prompt dla Gemini, który:
  - Zleca weryfikację ogłoszenia na podstawie kryteriów z `custom_prompt`.
  - Nakazuje zwrócić `ODRZUĆ` w przypadku braku dopasowania do kryteriów kampanii.
  - Zachowuje dotychczasowy prompt tylko dla kampanii bez zdefiniowanego `custom_prompt` (wsteczna kompatybilność).

### 2. Backend: Parser i Zapis Leadów (`src/database.py` -> `save_lead`)
- Rozszerzenie przypisywania pól obiektu `Lead` o alternatywne klucze słownika:
  - `tytul` = `lead_dict.get("tytul")` or `lead_dict.get("tytul_generowany")` or `lead_dict.get("nazwa_inwestycji")`
  - `inwestor` = `lead_dict.get("inwestor")` or `lead_dict.get("nazwa_inwestora")`
  - `zakres` = `lead_dict.get("zakres")` or `lead_dict.get("opis_szczegolowy")`
  - `uzasadnienie` = `lead_dict.get("uzasadnienie")` or `lead_dict.get("potencjal_handlowy")`
  - `data_pub` = `lead_dict.get("data")` or `lead_dict.get("termin_skladania")` or `lead_dict.get("data_pub")`

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator** (Ten agent): Definicja planu, merge i wdrożenie na VPS.
- **Builder** (Subagent): Modyfikacja `src/osint_engine.py` i `src/database.py` w worktree.
- **Auditor** (Subagent): Przegląd kodu pod kątem dopasowania pól parsera.
