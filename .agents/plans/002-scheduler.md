# PLAN-002: Task Scheduler & Engine Parameterization (Faza 2)

## 📊 Ewaluacja Opcji Harmonogramu

| Kryterium | Opcja A (Python Daemon / APScheduler w Dockerze) | Opcja B (Antigravity Native Task /schedule) |
| :--- | :--- | :--- |
| **Autonomia i Stabilność** | **Bardzo wysoka**: Działa niezależnie na VPS wewnątrz kontenera. 0 zależności zewnętrznych. | **Średnia**: Wymaga stałego połączenia z platformą agenta / IDE dewelopera do wyzwalania. |
| **Koszt tokenów LLM** | **0 tokenów**: Uruchomienie harmonogramu nie zużywa tokenów kontekstu (LLM jest wołany tylko do analizy ofert). | **Wysoki**: Każde wyzwolenie to start nowej pętli agenta, pobieranie repozytorium i kontekstu. |
| **Wygoda testowania** | Proste debugowanie lokalnie i w kontenerze. | Zależne od konfiguracji CLI dewelopera. |
| **Produkcyjność (SaaS)** | Standard branżowy dla samodzielnych mikroserwisów. | Przydatne do automatyzacji deweloperskich, nie do systemów produkcyjnych. |

### Rekomendacja: Opcja A (Python Daemon / APScheduler)
Opcja A jest jedynym stabilnym i ekonomicznym wyborem dla wewnętrznego narzędzia produkcyjnego. Pozwala na zachowanie 100% autonomii serwisu na VPS bez generowania zbędnych kosztów tokenów przy każdym pustym skanowaniu.

---

## 🏗️ Specyfikacja Implementacji Fazy 2

### 1. Dynamiczne Parametry w Silniku (`osint_engine.py`)
* Zostanie dodana obsługa przekazywania parametrów konta (`Account`) bezpośrednio do metody `run_search` oraz powiązanych metod (filtrowanie po CPV, słowach kluczowych i prompt systemowy).
* Logika BZP/GUNB wykorzysta indywidualną temperaturę i prompt skonfigurowany na koncie.

### 2. Logowanie "Twardych Dowodów" (`ResearchLog`)
* Każde uruchomienie potoku wyszukiwania (nawet jeśli nie znajdzie nowych leadów) musi wygenerować rekord w tabeli `research_logs`.
* Zapisujemy: `response_status_code` pobrany z API rządowych (lub kod 500 w razie awarii), oraz wygenerowany `raw_response_hash` (skrót SHA-256 z odpowiedzi tekstowej/JSON).

### 3. Dynamiczne Mapowanie Odoo Multicompany
* Klasa `OdooClient` w `odoo_integration.py` zostanie rozbudowana tak, aby przy tworzeniu leada dynamicznie przyjmować:
  * `company_id` (Odoo Company ID).
  * `user_id` (Odoo Salesperson User ID, przekazywany jako liczba lub `False` w celu pozostawienia pola pustego).
  * `tag_ids` (Lista tagów Odoo, mapowana na relację wiele-do-wielu w XML-RPC: `[(6, 0, tag_ids)]`).

---

## 🔎 Punkty Kontrolne i Kryteria Testowe dla Auditora
1. Czy wywołanie skanowania bez nowych leadów poprawnie tworzy rekord w `ResearchLog` z kodem statusu (np. 200) i hashem SHA-256?
2. Czy przekazanie `user_id=None` (lub `False`) w konfiguracji konta skutkuje poprawnym utworzeniem leada w Odoo bez przypisanego handlowca (pole puste)?
3. Czy tagi Odoo są przesyłane w formacie komendy XML-RPC M2M (`[(6, 0, tag_ids)]`) i poprawnie przypisywane w CRM?
