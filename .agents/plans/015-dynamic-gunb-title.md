# PLAN-015: Dynamiczny Tytuł Leadu w Rejestrze Pozwoleń Budowlanych (GUNB)

## 🎯 Cel Projektowy
Wykryto, że w pliku `src/osint_engine.py` w metodzie `_search_gunb()` tytuł leada jest na sztywno zdefiniowany jako `"Budowa wagi samochodowej - {inwestor}"`. W przypadku kampanii innych niż wagi samochodowe (np. wagi przemysłowe, wzorcowania) wygenerowane leady z rejestru GUNB miałyby błędne, twardo zakodowane nazwy. Celem jest dynamiczne generowanie tytułu w oparciu o nazwę aktywnej kampanii (Account).

---

## 🏗️ Specyfikacja Zmian

### 1. Silnik OSINT (`src/osint_engine.py`)
- Wewnątrz metody `_search_gunb`:
  - Pobranie nazwy kampanii: `campaign_name = account.name if account else "Budowa wagi samochodowej"`.
  - Ustawienie tytułu leada na: `f"{campaign_name} - {inwestor or 'Inwestor prywatny'}"`.

---

## 🛠️ Podział Ról (Swarm Triad)
- **Coordinator** (Ten agent): Definicja planu, merge i wdrożenie na VPS.
- **Builder** (Subagent): Modyfikacja pliku `src/osint_engine.py` w worktree.
- **Auditor** (Subagent): Przegląd kodu pod kątem poprawności.
