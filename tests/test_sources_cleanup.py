"""
test_sources_cleanup.py — Testy jednostkowe weryfikujące oczyszczenie listy źródeł OSINT (Plan 068).
"""

import pytest
from main import get_available_sources
from scrapers.factory import (
    CANONICAL_SCRAPERS,
    get_scraper_for_source,
    SCRAPER_REGISTRY,
    NORMALIZED_REGISTRY,
)
from scrapers.automatyka import AutomatykaScraper
from scrapers.logintrade import LogintradeScraper
from scrapers.biznes_polska import BiznesPolskaScraper
from scrapers.baza_konkurenconosci import BazaKonkurenconosciScraper
from scrapers.platforma_zakupowa import PlatformaZakupowaScraper


EXPECTED_CANONICAL_IDS = {
    "BZP",
    "Google",
    "GUNB",
    "Automatyka",
    "BazaKonkurencyjnosci",
    "BiznesPolska",
    "LoginTrade",
    "PlatformaZakupowa",
}

FORBIDDEN_ALIAS_IDS = {
    "logintrade",
    "bazakonkurenconosci",
    "bazakonkurencyjnosci",
    "platformazakupowa",
    "PlatformaZakupowa.pl",
    "automatyka",
    "biznespolska",
    "Biznes-Polska",
    "bk2021",
    "opennexus",
}


@pytest.mark.asyncio
async def test_get_available_sources_count_and_canonical_ids():
    """Test async endpoint get_available_sources() returns exactly 8 items with expected canonical IDs."""
    sources = await get_available_sources()

    assert len(sources) == 8, f"Expected exactly 8 sources, got {len(sources)}: {[s['id'] for s in sources]}"

    source_ids = [s["id"] for s in sources]
    # Sprawdzenie unikalności ID
    assert len(source_ids) == len(set(source_ids)), f"Duplicate source IDs detected: {source_ids}"

    # Sprawdzenie zgodności ze zbiorem kanonicznych ID
    assert set(source_ids) == EXPECTED_CANONICAL_IDS


@pytest.mark.asyncio
async def test_get_available_sources_no_duplicate_aliases():
    """Test weryfikujący brak jakichkolwiek aliasów w liście zwracanej przez endpoint."""
    sources = await get_available_sources()
    source_ids = {s["id"] for s in sources}

    for forbidden_id in FORBIDDEN_ALIAS_IDS:
        assert forbidden_id not in source_ids, f"Forbidden alias '{forbidden_id}' found in /api/sources list"


@pytest.mark.asyncio
async def test_get_available_sources_structure():
    """Test weryfikujący poprawność struktury metadanych źródeł (id, name, description, is_plugin)."""
    sources = await get_available_sources()

    for s in sources:
        assert "id" in s and s["id"]
        assert "name" in s and s["name"]
        assert "description" in s and s["description"]
        assert "is_plugin" in s
        assert isinstance(s["is_plugin"], bool)

    plugins = [s for s in sources if s["is_plugin"]]
    builtins = [s for s in sources if not s["is_plugin"]]

    assert len(builtins) == 3  # BZP, Google, GUNB
    assert len(plugins) == 5   # Automatyka, BazaKonkurencyjnosci, BiznesPolska, LoginTrade, PlatformaZakupowa


def test_scraper_factory_alias_resolution_preserved():
    """Test weryfikujący, że get_scraper_for_source nadal bezbłędnie rozwiązuje aliasy mimo oczyszczenia API."""
    # LoginTrade aliasy
    for alias in ["LoginTrade", "Logintrade", "logintrade", "logintrade.pl", "LOGIN-TRADE"]:
        scraper = get_scraper_for_source(alias)
        assert scraper is not None, f"Failed resolving alias '{alias}'"
        assert isinstance(scraper, LogintradeScraper)

    # BazaKonkurencyjnosci aliasy
    for alias in ["BazaKonkurencyjnosci", "BazaKonkurenconosci", "bazakonkurencyjnosci", "bazakonkurenconosci", "bk2021", "bazakonkurencyjnosci.gov.pl"]:
        scraper = get_scraper_for_source(alias)
        assert scraper is not None, f"Failed resolving alias '{alias}'"
        assert isinstance(scraper, BazaKonkurenconosciScraper)

    # PlatformaZakupowa aliasy
    for alias in ["PlatformaZakupowa", "platformazakupowa", "PlatformaZakupowa.pl", "platforma-zakupowa.pl", "opennexus"]:
        scraper = get_scraper_for_source(alias)
        assert scraper is not None, f"Failed resolving alias '{alias}'"
        assert isinstance(scraper, PlatformaZakupowaScraper)

    # BiznesPolska aliasy
    for alias in ["BiznesPolska", "Biznes-Polska", "biznespolska", "biznes-polska.pl"]:
        scraper = get_scraper_for_source(alias)
        assert scraper is not None, f"Failed resolving alias '{alias}'"
        assert isinstance(scraper, BiznesPolskaScraper)

    # Automatyka aliasy
    for alias in ["Automatyka", "automatyka", "automatyka.pl"]:
        scraper = get_scraper_for_source(alias)
        assert scraper is not None, f"Failed resolving alias '{alias}'"
        assert isinstance(scraper, AutomatykaScraper)


def test_canonical_scrapers_registry():
    """Test weryfikujący słownik CANONICAL_SCRAPERS."""
    assert len(CANONICAL_SCRAPERS) == 5
    for key in ["Automatyka", "BazaKonkurencyjnosci", "BiznesPolska", "LoginTrade", "PlatformaZakupowa"]:
        assert key in CANONICAL_SCRAPERS
        entry = CANONICAL_SCRAPERS[key]
        assert "class" in entry
        assert "name" in entry
        assert "description" in entry
