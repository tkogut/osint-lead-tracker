"""
factory.py — Fabryka i rejestr wtyczek skraperów.
"""

from typing import Dict, Type, Optional
from scrapers.base import BaseScraper
from scrapers.automatyka import AutomatykaScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "Automatyka": AutomatykaScraper,
}


def get_scraper_for_source(source_name: str) -> Optional[BaseScraper]:
    """
    Zwraca instancję zarejestrowanego skrapera dla podanej nazwy źródła,
    lub None jeśli źródło korzysta ze starego potoku (np. BZP, GUNB, Google).
    """
    scraper_cls = SCRAPER_REGISTRY.get(source_name)
    if scraper_cls:
        return scraper_cls()
    return None
