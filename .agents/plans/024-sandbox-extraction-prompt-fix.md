# PLAN-024: Naprawa Ekstrakcji Leada z Surowego Tekstu w Piaskownicy AI

**Status:** COMPLETED / DONE  
**Data realizacji:** 2026-07-22  


---

## 🎯 Cel Projektowy
Poprawa budowy zapytania do Gemini w `POST /api/sandbox/test` przy testowaniu surowego tekstu / URL, aby dostarczyć kontekst wyciągania danych leada do JSON, identycznie jak w produkcyjnej funkcji `_extract_lead_from_raw_text`.

---

## 🏗️ Specyfikacja Zmian

1. **Backend API (`src/main.py`)**:
   - Konstruowanie `user_contents` dla testów surowego tekstu / URL w Piaskownicy z wytycznymi ekstrakcji `{"leady": [...]}`.
