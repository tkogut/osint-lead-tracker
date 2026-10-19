"""
scrapers package — Dedykowane wtyczki skraperów dla osint-lead-tracker.
"""

from scrapers.base import BaseScraper, DOMSanitizer
from scrapers.factory import get_scraper_for_source, SCRAPER_REGISTRY, CANONICAL_SCRAPERS
from scrapers.logintrade import LogintradeScraper
from scrapers.platforma_zakupowa import PlatformaZakupowaScraper

__all__ = [
    "BaseScraper",
    "DOMSanitizer",
    "get_scraper_for_source",
    "SCRAPER_REGISTRY",
    "CANONICAL_SCRAPERS",
    "LogintradeScraper",
    "PlatformaZakupowaScraper",
]
