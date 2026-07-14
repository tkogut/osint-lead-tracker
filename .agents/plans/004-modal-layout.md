# PLAN-004: Przebudowa Layoutu Modalnego Kont / Kampanii

## 🎯 Cel Biznesowy
Ułatwienie edycji i czytelności długich promptów systemowych (Dedykowany Prompt Systemowy) poprzez podział modalnego okna edycji kampanii na dwie szerokie kolumny (Ustawienia po lewej, Prompt po prawej).

---

## 🏗️ Specyfikacja Zmian w Kodzie

### 1. HTML (`src/static/index.html`)
* Kontenery pól formularza w modalu `#account-modal` zostaną otoczone nową strukturą gridu:
  * `.modal-two-columns` (kontener główny).
  * `.modal-col-left` (wszystkie dotychczasowe pola tekstowe, CPV, słowa kluczowe, mapowania Odoo).
  * `.modal-col-right` (tylko okno promptu systemowego z rozciągnięciem do pełnej wysokości).

### 2. CSS (`src/static/styles.css`)
* Rozszerzenie szerokości modalu:
  * `.modal-content`: Zmiana z `width: 650px` na `width: 1050px` (oraz `max-width: 95vw`).
* Klasy pozycjonujące:
  * `.modal-two-columns`: `display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px;`
  * `.modal-col-right textarea`: Ustawienie `height: calc(100% - 30px); min-height: 480px; resize: none;` w celu wykorzystania pełnej wysokości kolumny.

---

## 🛠️ Podział Ról (Swarm Triad)
* **Coordinator**: Zarządzanie planowaniem, backlogiem (`task.md`), commitami i deployem.
* **Builder** (Subagent `swarm_builder`): Wykonanie zmian w plikach HTML i CSS.
* **Auditor** (Subagent `swarm_auditor`): Weryfikacja wizualna i strukturalna kodu.
