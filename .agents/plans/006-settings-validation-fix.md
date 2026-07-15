# PLAN-006: Poprawka Walidacji Maskowanych Kluczy w Ustawieniach (FastAPI)

## 🎯 Cele Projektowe
Usunięcie błędu uniemożliwiającego zapis pozostałych konfiguracji w panelu Ustawień, wywoływanego przez walidację wartości maskowanych (np. `...`).

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. Backend (FastAPI - `src/main.py`)
* Zmiana w endpointcie `PUT /api/settings`:
  * Jeżeli przesyłana wartość klucza zawiera znaki maskujące `...`, traktujemy ją jako niezmienioną przez użytkownika (placeholder).
  * Backend powinien zignorować aktualizację dla tego konkretnego ustawienia i zwrócić status sukcesu (`{"success": True}`) zamiast zgłaszać błąd 400 (`HTTPException`).
  * Pozwoli to na bezproblemowy zapis pozostałych (zmodyfikowanych) pól konfiguracji bez potrzeby ponownego wpisywania sekretów.

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator**: Zarządzanie planem, backlogiem i VPS.
* **Builder**: Modyfikacja pliku `src/main.py` w celu obsługi wartości maskowanych.
* **Auditor**: Weryfikacja poprawności zachowania endpointu.
