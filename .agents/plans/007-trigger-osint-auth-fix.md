# PLAN-007: Poprawka Autoryzacji Ręcznego Uruchamiania Skanowania (FastAPI)

## 🎯 Cele Projektowe
Umożliwienie poprawnego wywołania endpointu `/trigger-osint` z poziomu panelu administracyjnego (frontendu) bez występowania błędu 401 Unauthorized wywoływanego przez maskowanie tokenu API.

---

## 🏗️ Specyfikacja Architektury i Zmian

### 1. Backend (FastAPI - `src/main.py`)
* Zmiana autoryzacji w endpoincie `/trigger-osint`:
  * Aktualnie endpoint wymaga wyłącznie nagłówka `X-API-Token` (poprzez zależność `verify_token`).
  * Ponieważ `API_TOKEN` jest maskowany w ustawieniach (zwracany jako np. `abc...xyz`), frontend przesyła niepoprawny token i otrzymuje błąd 401.
  * Zmienimy zależność autoryzacji w `/trigger-osint` na nową funkcję `verify_token_or_session`.
  * Funkcja ta najpierw sprawdzi ważność sesji użytkownika (cookie `session_token`), a w przypadku jej braku lub niepoprawności – zweryfikuje nagłówek `X-API-Token` (na potrzeby zewnętrznych integracji).

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator**: Zarządzanie planem, backlogiem i VPS.
* **Builder**: Implementacja `verify_token_or_session` w `src/main.py` oraz aktualizacja endpointu `/trigger-osint`.
* **Auditor**: Weryfikacja działania z poziomu sesji przeglądarki oraz zewnętrznych skryptów.
