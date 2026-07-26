# Plan Wdrożenia: Obsługa odmiany polskich słów kluczowych (PRD)

## Cel projektu
Wdrożenie hybrydowego mechanizmu obsługi odmiany słów kluczowych w języku polskim w celu eliminacji pomijania leadów z powodu końcówek fleksyjnych (np. "waga samochodowa" -> "wag samochodowych", "wagi do samochodów").

Rozwiązanie składa się z dwóch uzupełniających się modułów:
1. **Ekspansja słów kluczowych przez AI w panelu konfiguracyjnym (Settings)**:
   Przed zapisem nowej lub zaktualizowanej kampanii w bazie danych, system automatycznie rozszerzy zdefiniowane słowa kluczowe o najpopularniejsze formy gramatyczne za pomocą jednorazowego zapytania do Gemini (`gemini-2.5-flash`).
2. **Dopasowanie tematów słów (Stemming/Regex Matcher) w scraperach**:
   Klasa bazowa oraz silnik OSINT zostaną wyposażone w algorytm sprawdzania bliskości rdzeni słów (stems) w oknie tekstowym, aby wyłapać odmiany bez spadku wydajności na VPS.

---

## User Review Required
> [!IMPORTANT]
> **Aktualizacja struktury słów kluczowych**:
> Po wdrożeniu zmian, każde nowo utworzone konto lub edytowane słowa kluczowe automatycznie przejdą ekspansję AI. Dla istniejących kont (np. Agro) zostanie automatycznie uruchomiona migracja w bazie danych podczas uruchomienia kontenera, aby nie było potrzeby manualnej rekonfiguracji.

---

## Proposed Changes

### 1. Nowy moduł pomocniczy
#### [NEW] `src/utils.py`
Utworzenie modułu z helperem `match_polish_keywords(text, keywords)`.

```python
import re
from typing import List

def match_polish_keywords(text: str, keywords: List[str]) -> bool:
    """
    Weryfikuje, czy tekst zawiera słowa kluczowe z uwzględnieniem odmian.
    1. Dopasowanie bezpośrednie (podciągi + formy AI).
    2. Dopasowanie bliskości tematów (stems) w oknie 120 znaków (np. 'waga' + 'samochodowa').
    """
    if not keywords:
        return True
        
    text_lower = text.lower()
    
    # Krok 1: Bezpośrednie dopasowanie
    for kw in keywords:
        kw_clean = kw.lower().strip()
        if not kw_clean:
            continue
        if kw_clean in text_lower:
            return True
            
    # Krok 2: Uproszczony stemmer i dopasowanie bliskości dla fraz wielowyrazowych
    for kw in keywords:
        words = [w for w in re.findall(r'\b\w+\b', kw.lower()) if len(w) > 3]
        if not words:
            continue
            
        stems = []
        for w in words:
            stem = w[:-1] if w[-1] in 'aeiouyęąó' else w
            if len(stem) > 3:
                if stem.endswith('ód'):
                    stem = stem[:-2] + 'od'
                elif stem[-1] in 't':
                    stem = stem[:-1]
            stems.append(stem)
            
        if not stems:
            continue
            
        found_all = True
        for stem in stems:
            if stem not in text_lower:
                found_all = False
                break
                
        if found_all:
            # Weryfikacja współwystępowania w oknie 120 znaków wokół pierwszego dopasowania
            for match in re.finditer(re.escape(stems[0]), text_lower):
                start_pos = max(0, match.start() - 60)
                end_pos = min(len(text_lower), match.end() + 120)
                window = text_lower[start_pos:end_pos]
                if all(stem in window for stem in stems):
                    return True
                    
    return False
```

---

### 2. Integracja w Scraperach i Silniku OSINT
#### [MODIFY] `src/scrapers/automatyka.py`
#### [MODIFY] `src/scrapers/logintrade.py`
#### [MODIFY] `src/scrapers/biznes_polska.py`
#### [MODIFY] `src/scrapers/baza_konkurenconosci.py`
Zastąpienie `any(k in text_lower for k in keywords)` wywołaniem `match_polish_keywords(text_lower, keywords)`.

#### [MODIFY] `src/osint_engine.py`
- Zastąpienie prostego dopasowania w pętli BZP (`any(k in title_lower or k in body_lower)`) przez wywołanie `match_polish_keywords`.
- Dostosowanie funkcji `_verify_bzp_notice` oraz filtrowania RWDZ GUNB.

---

### 3. API i Ekspansja AI (Settings)
#### [MODIFY] `src/main.py`
- Dodanie funkcji `async def expand_keywords_via_ai(keywords: List[str], db_session) -> List[str]`, która odpytuje model `gemini-2.5-flash` o wygenerowanie odmian słów kluczowych.
- Wdrożenie automatycznego wywołania tej metody w endpointach `create_account` oraz `update_account` przed zapisem zmian do bazy danych.

---

## Verification Plan

### Automated Tests
1. **Utworzenie testów jednostkowych**:
   Stworzenie `tests/test_polish_keywords.py` w celu walidacji funkcji `match_polish_keywords` (formy bezpośrednie, odmiany, bliskość wyrazów w oknie).
2. **Uruchomienie wszystkich testów**:
   ```bash
   PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
   ```

### Manual Verification
1. Wyszukanie w Sandboxie adresu URL z niestandardową odmianą (np. z frazą "wagi samochodowej") i potwierdzenie, że scraper ją wykrywa.
2. Zapisanie nowej kampanii w panelu i weryfikacja w bazie danych (SQLite), że pole `target_keywords` zostało rozszerzone o odmiany wygenerowane przez AI.
