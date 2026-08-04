# Plan Wdrożenia: System ostrzeżeń i powiadomień o nieobsługiwanych modelach (PRD)

## Cel projektu
Wdrożenie mechanizmu automatycznego powiadamiania użytkownika (w formie alertu na pulpicie/dashboardzie oraz czytelnego oznaczenia przy kampanii), gdy któraś z aktywnych kampanii korzysta z modelu Gemini, który przestał być obsługiwany przez API Google Gemini.

---

## Proposed Changes

### 1. Modyfikacja [src/static/index.html](file:///home/tkogut/projects/osint-lead-tracker/src/static/index.html)
- Dodanie dedykowanego baneru ostrzegawczego `#model-failure-banner` (tuż pod `#api-failure-banner`), wyświetlającego informację o wykryciu nieobsługiwanych modeli w aktywnych kampaniach.

### 2. Modyfikacja [src/static/app.js](file:///home/tkogut/projects/osint-lead-tracker/src/static/app.js)
- Zdefiniowanie zmiennej stanu `let availableModelsList = [];`.
- Zapisanie listy załadowanych modeli z `/api/available-models` do `availableModelsList`.
- Zaimplementowanie funkcji `checkCampaignModelsIntegrity()`, która porównuje modele skonfigurowane w aktywnych kampaniach z listą `availableModelsList`. Jeśli jakaś kampania ma przypisany nieobsługiwany model, wyświetlany jest baner ostrzegawczy wraz z nazwami tych kampanii.
- Aktualizacja funkcji `renderAccounts(accounts)` w celu wyświetlania ostrzeżenia `(Nieobsługiwany!)` na karcie kampanii, jeśli dany model nie jest dostępny.
- Uruchamianie weryfikacji w `showAppScreen()` po zalogowaniu oraz w `loadAccountsData()` po odświeżeniu kampanii.
