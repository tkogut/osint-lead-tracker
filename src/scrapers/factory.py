"""
factory.py — Fabryka i rejestr wtyczek skraperów.
"""

import re
from typing import Dict, Type, Optional, Any
from scrapers.base import BaseScraper
from scrapers.automatyka import AutomatykaScraper
from scrapers.logintrade import LogintradeScraper
from scrapers.biznes_polska import BiznesPolskaScraper
from scrapers.baza_konkurenconosci import BazaKonkurenconosciScraper
from scrapers.platforma_zakupowa import PlatformaZakupowaScraper



def normalize_source_name(name: str) -> str:
    """
    Normalizuje nazwę źródła skrapera:
    - oczyszczenie z białych znaków, małe litery
    - zamiana polskich znaków diakrytycznych na litery łacińskie
    - usunięcie końcówek domenowych (.gov.pl, .com.pl, .pl, .com itp.)
    - usunięcie znaków niealfanumerycznych ([^a-z0-9])
    """
    if not name or not isinstance(name, str):
        return ""
    s = name.strip().lower()

    # Zamiana polskich znaków diakrytycznych
    polish_trans = str.maketrans({
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z"
    })
    s = s.translate(polish_trans)

    # Usunięcie końcówek domenowych
    for ext in (
        ".gov.pl", ".com.pl", ".net.pl", ".org.pl",
        ".com", ".pl", ".net", ".org", ".eu", ".info"
    ):
        if s.endswith(ext):
            s = s[:-len(ext)]
            break

    # Usunięcie znaków niealfanumerycznych
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


# Kanoniczny rejestr wtyczek skraperów z metadanymi dla API i UI
CANONICAL_SCRAPERS: Dict[str, Dict[str, Any]] = {
    "Automatyka": {
        "class": AutomatykaScraper,
        "name": "Automatyka.pl (Zapytania B2B)",
        "description": "Darmowe. Zapytania techniczne, komponenty, automatyka przemysłowa."
    },
    "BazaKonkurencyjnosci": {
        "class": BazaKonkurenconosciScraper,
        "name": "Baza Konkurencyjności (BK2021 / Dotacje UE)",
        "description": "Darmowe. Zamówienia publiczne i prywatne z funduszy UE / KPO."
    },
    "BiznesPolska": {
        "class": BiznesPolskaScraper,
        "name": "Biznes-Polska (Przetargi i Inwestycje)",
        "description": "Darmowe (wymagana subskrypcja). Agregacja zamówień publicznych i komercyjnych."
    },
    "LoginTrade": {
        "class": LogintradeScraper,
        "name": "LoginTrade (Przemysł i Spółki SP)",
        "description": "Darmowe. Platforma zakupowa spółek skarbu państwa i przemysłu ciężkiego."
    },
    "PlatformaZakupowa": {
        "class": PlatformaZakupowaScraper,
        "name": "PlatformaZakupowa.pl (Gminy, PSZOK, Wodociągi)",
        "description": "Darmowe. Przetargi i zapytania jednostek samorządowych i komunalnych."
    }
}


# Rejestr dokładnych nazw (zachowuje wsteczną kompatybilność oraz popularne aliasy)
SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    # Oryginalne klucze
    "Automatyka": AutomatykaScraper,
    "Logintrade": LogintradeScraper,
    "BiznesPolska": BiznesPolskaScraper,
    "BazaKonkurenconosci": BazaKonkurenconosciScraper,
    "PlatformaZakupowa": PlatformaZakupowaScraper,
    # Popularne aliasy i warianty wielkości liter
    "LoginTrade": LogintradeScraper,
    "logintrade": LogintradeScraper,
    "BazaKonkurencyjnosci": BazaKonkurenconosciScraper,
    "bazakonkurencyjnosci": BazaKonkurenconosciScraper,
    "bazakonkurenconosci": BazaKonkurenconosciScraper,
    "Biznes-Polska": BiznesPolskaScraper,
    "biznespolska": BiznesPolskaScraper,
    "automatyka": AutomatykaScraper,
    "platformazakupowa": PlatformaZakupowaScraper,
    "PlatformaZakupowa.pl": PlatformaZakupowaScraper,
}

# Rejestr znormalizowanych ciągów znaków (po normalizacji funkcją normalize_source_name)
NORMALIZED_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "automatyka": AutomatykaScraper,
    "logintrade": LogintradeScraper,
    "biznespolska": BiznesPolskaScraper,
    "bazakonkurencyjnosci": BazaKonkurenconosciScraper,
    "bazakonkurenconosci": BazaKonkurenconosciScraper,
    "bk2021": BazaKonkurenconosciScraper,
    "platformazakupowa": PlatformaZakupowaScraper,
    "opennexus": PlatformaZakupowaScraper,
}


def get_scraper_for_source(source_name: str) -> Optional[BaseScraper]:
    """
    Zwraca instancję zarejestrowanego skrapera dla podanej nazwy źródła,
    lub None jeśli źródło korzysta ze starego potoku (np. BZP, GUNB, Google) lub jest nieznane.

    Najpierw wyszukuje dokładne dopasowanie w SCRAPER_REGISTRY,
    a w przypadku braku – szuka w NORMALIZED_REGISTRY po znormalizowanej nazwie.
    """
    if not source_name or not isinstance(source_name, str):
        return None

    scraper_cls = SCRAPER_REGISTRY.get(source_name)
    if not scraper_cls:
        norm_name = normalize_source_name(source_name)
        scraper_cls = NORMALIZED_REGISTRY.get(norm_name)

    if scraper_cls:
        return scraper_cls()
    return None
