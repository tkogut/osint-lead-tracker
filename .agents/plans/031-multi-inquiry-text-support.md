# PLAN-031: Universal Multi-Inquiry Listing Extraction Rule

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Upgrade LLM text extraction rules globally in `src/osint_engine.py` and `src/main.py` using **100% generic and universal instructions** (NO hardcoded brands, product names, or domain words).

---

## 🏗️ Universal Rule Specification
```text
OBSŁUGA STRON ZBIORCZYCH I WIELOKROTNYCH ZAPYTAŃ:
1. Przekazana treść może stanowić stronę zbiorczą, zestawienie kategorialne lub agregator zapytań zawierający wiele różnych produktów lub usług.
2. Przeszukaj cały tekst i WYEKSTRAHUJ WSZYSTKIE POJEDYNCZE OGŁOSZENIA/ZAPYTANIA, których treść ściśle odpowiada wymaganiom kampanii zdefiniowanym w system_instruction.
3. Ignoruj wszelkie inne wpisy, produkty i ogłoszenia w tekście, które NIE ODPOWIADAJĄ kryteriom kampanii.
4. Zwróć każdy pasujący lead w strukturze JSON {"leady": [...]}. Jeśli żaden wpis w tekście nie odpowiada wymaganiom kampanii, zwróć {"leady": []}.
```

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.9).
- **Builder (Subagent)**: Implement generic prompt rules in `src/osint_engine.py` and `src/main.py`, verify syntax, and generate builder handshake.
