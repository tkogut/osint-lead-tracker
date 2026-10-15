"""
test_scraper_factory_aliases.py — Testy jednostkowe dla normalizacji nazw źródeł skraperów i obsługi aliasów (Plan 066 / Issue #5).
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from scrapers.factory import (
    normalize_source_name,
    get_scraper_for_source,
    SCRAPER_REGISTRY,
    NORMALIZED_REGISTRY,
)
from scrapers.automatyka import AutomatykaScraper
from scrapers.logintrade import LogintradeScraper
from scrapers.biznes_polska import BiznesPolskaScraper
from scrapers.baza_konkurenconosci import BazaKonkurenconosciScraper
from scrapers.platforma_zakupowa import PlatformaZakupowaScraper
from osint_engine import OSINTEngine


class DummyAccount:
    """Mock obiektu konta/kampanii do testów routingu źródeł."""
    def __init__(self, name="Test Account", enabled_sources=None):
        self.id = 1
        self.name = name
        self.enabled_sources = json.dumps(enabled_sources) if enabled_sources is not None else None
        self.target_cpvs = json.dumps(["42923110-6"])
        self.target_keywords = json.dumps(["waga samochodowa"])
        self.custom_prompt = None
        self.llm_model = "gemini-2.5-flash"
        self.grounding_llm_model = "gemini-2.5-flash"
        self.llm_temperature = 0.1
        self.llm_max_tokens = 4096


class TestScraperFactoryNormalization(unittest.TestCase):
    def test_normalize_source_name_basic(self):
        self.assertEqual(normalize_source_name("Logintrade"), "logintrade")
        self.assertEqual(normalize_source_name("LoginTrade"), "logintrade")
        self.assertEqual(normalize_source_name("  Automatyka  "), "automatyka")
        self.assertEqual(normalize_source_name("BIZNES-POLSKA"), "biznespolska")

    def test_normalize_source_name_domain_suffixes(self):
        self.assertEqual(normalize_source_name("PlatformaZakupowa.pl"), "platformazakupowa")
        self.assertEqual(normalize_source_name("platforma-zakupowa.com"), "platformazakupowa")
        self.assertEqual(normalize_source_name("bazakonkurencyjnosci.gov.pl"), "bazakonkurencyjnosci")
        self.assertEqual(normalize_source_name("logintrade.net.pl"), "logintrade")
        self.assertEqual(normalize_source_name("ezamowienia.gov.pl"), "ezamowienia")

    def test_normalize_source_name_polish_diacritics(self):
        self.assertEqual(normalize_source_name("Baza Konkurencyjności"), "bazakonkurencyjnosci")
        self.assertEqual(normalize_source_name("Żółta Waga"), "zoltawaga")

    def test_normalize_source_name_empty_and_invalid(self):
        self.assertEqual(normalize_source_name(""), "")
        self.assertEqual(normalize_source_name(None), "")
        self.assertEqual(normalize_source_name(123), "")


class TestScraperFactoryResolution(unittest.TestCase):
    def test_get_scraper_logintrade_variants(self):
        for name in ["Logintrade", "LoginTrade", "logintrade", "logintrade.pl", "LOGIN-TRADE"]:
            scraper = get_scraper_for_source(name)
            self.assertIsNotNone(scraper, f"Failed for {name}")
            self.assertIsInstance(scraper, LogintradeScraper)

    def test_get_scraper_bazakonkurencyjnosci_variants(self):
        for name in [
            "BazaKonkurenconosci",
            "BazaKonkurencyjnosci",
            "bazakonkurencyjnosci",
            "bazakonkurenconosci",
            "bazakonkurencyjnosci.gov.pl",
            "bk2021",
            "Baza Konkurencyjności",
        ]:
            scraper = get_scraper_for_source(name)
            self.assertIsNotNone(scraper, f"Failed for {name}")
            self.assertIsInstance(scraper, BazaKonkurenconosciScraper)

    def test_get_scraper_biznes_polska_variants(self):
        for name in ["BiznesPolska", "Biznes-Polska", "biznespolska", "biznes-polska.pl"]:
            scraper = get_scraper_for_source(name)
            self.assertIsNotNone(scraper, f"Failed for {name}")
            self.assertIsInstance(scraper, BiznesPolskaScraper)

    def test_get_scraper_platforma_zakupowa_variants(self):
        for name in [
            "PlatformaZakupowa",
            "platformazakupowa",
            "PlatformaZakupowa.pl",
            "platforma-zakupowa.pl",
            "opennexus",
        ]:
            scraper = get_scraper_for_source(name)
            self.assertIsNotNone(scraper, f"Failed for {name}")
            self.assertIsInstance(scraper, PlatformaZakupowaScraper)

    def test_get_scraper_automatyka_variants(self):
        for name in ["Automatyka", "automatyka", "automatyka.pl", "AUTOMATYKA"]:
            scraper = get_scraper_for_source(name)
            self.assertIsNotNone(scraper, f"Failed for {name}")
            self.assertIsInstance(scraper, AutomatykaScraper)

    def test_get_scraper_unknown_and_builtin(self):
        # Unknown sources should return None
        self.assertIsNone(get_scraper_for_source("NieznaneZrodlo"))
        self.assertIsNone(get_scraper_for_source("unknown_platform"))
        self.assertIsNone(get_scraper_for_source(""))
        self.assertIsNone(get_scraper_for_source(None))

        # Built-in sources return None (they are handled in OSINTEngine)
        self.assertIsNone(get_scraper_for_source("BZP"))
        self.assertIsNone(get_scraper_for_source("Google"))
        self.assertIsNone(get_scraper_for_source("GUNB"))


class TestOSINTEngineSourceRouting(unittest.TestCase):
    def setUp(self):
        self.engine = OSINTEngine()

    @patch.object(OSINTEngine, "_search_bzp", return_value=([], 200, "bzp_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_google", return_value=([], 200, "google_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_gunb", return_value=([], 200, "gunb_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_plugin", return_value=([], 200, "plugin_hash", 0, 0, 0, 0))
    def test_scan_all_sources_builtin_aliases(self, mock_plugin, mock_gunb, mock_google, mock_bzp):
        # Test routing for built-in source aliases
        account = DummyAccount(enabled_sources=[
            "ezamowienia.gov.pl",
            "googlesearch",
            "gunb-rwdz",
        ])

        results = self.engine.scan_all_sources(account)

        mock_bzp.assert_called_once()
        mock_google.assert_called_once()
        mock_gunb.assert_called_once()
        mock_plugin.assert_not_called()

        self.assertIn("BZP", results)
        self.assertIn("Google", results)
        self.assertIn("GUNB", results)

    @patch.object(OSINTEngine, "_search_bzp", return_value=([], 200, "bzp_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_google", return_value=([], 200, "google_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_gunb", return_value=([], 200, "gunb_hash", 0, 0, 0, 0))
    @patch.object(OSINTEngine, "_search_plugin", return_value=([], 200, "plugin_hash", 0, 0, 0, 0))
    def test_scan_all_sources_plugin_aliases(self, mock_plugin, mock_gunb, mock_google, mock_bzp):
        # Test routing for scraper plugin aliases (Issue #5 regression test)
        account = DummyAccount(enabled_sources=[
            "LoginTrade",
            "BazaKonkurencyjnosci",
            "Biznes-Polska",
            "PlatformaZakupowa.pl",
        ])

        results = self.engine.scan_all_sources(account)

        mock_bzp.assert_not_called()
        mock_google.assert_not_called()
        mock_gunb.assert_not_called()
        self.assertEqual(mock_plugin.call_count, 4)

        self.assertIn("LoginTrade", results)
        self.assertIn("BazaKonkurencyjnosci", results)
        self.assertIn("Biznes-Polska", results)
        self.assertIn("PlatformaZakupowa.pl", results)

    @patch.object(OSINTEngine, "scan_all_sources")
    def test_run_search_for_account_delegation(self, mock_scan):
        mock_scan.return_value = {"BZP": ([], 200, "h", 0, 0, 0, 0)}
        account = DummyAccount()
        res = self.engine.run_search_for_account(account, search_window_days=3)

        mock_scan.assert_called_once_with(account=account, search_window_days=3)
        self.assertEqual(res, {"BZP": ([], 200, "h", 0, 0, 0, 0)})


if __name__ == "__main__":
    unittest.main()
