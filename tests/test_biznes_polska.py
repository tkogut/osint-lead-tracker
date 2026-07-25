"""
test_biznes_polska.py — Testy jednostkowe dla biznes_polska.py
"""

import unittest
from unittest.mock import patch, AsyncMock
from scrapers.biznes_polska import BiznesPolskaScraper


class TestBiznesPolskaScraperAsync(unittest.IsolatedAsyncioTestCase):
    @patch("scrapers.biznes_polska.AsyncSession")
    @patch("scrapers.biznes_polska.fetch_multiple_with_playwright")
    @patch("scrapers.biznes_polska.is_url_visited")
    @patch("scrapers.biznes_polska.mark_url_visited")
    async def test_fetch_leads_two_phase(self, mock_mark_visited, mock_is_visited, mock_fetch_multi, mock_session_cls):
        # 1. Setup mock DB calls
        mock_is_visited.return_value = False
        
        # 2. Setup mock session (curl_cffi)
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mock main list page response (returns links to detail page)
        mock_list_resp = AsyncMock()
        mock_list_resp.status_code = 200
        mock_list_resp.text = """
        <html>
        <body>
            <a href="/przetargi/dostawa-wag-samochodowych,123456/">Szczegóły przetargu</a>
        </body>
        </html>
        """
        
        # Mock detail page response (Phase 1)
        mock_detail_resp = AsyncMock()
        mock_detail_resp.status_code = 200
        mock_detail_resp.text = """
        <html>
        <body>
            <h1>Dostawa wag samochodowych w roku 2026</h1>
            <p>Data dodania: 2026-07-25</p>
            <p>Opis: Szukamy wagi najazdowej.</p>
        </body>
        </html>
        """
        
        mock_empty_list = AsyncMock()
        mock_empty_list.status_code = 200
        mock_empty_list.text = "<html><body>No links here</body></html>"
        
        responses = [mock_list_resp, mock_detail_resp] + [mock_empty_list] * 9
        mock_session.get.side_effect = responses
        
        # 3. Setup mock Playwright multiple fetch (Phase 2)
        mock_fetch_multi.return_value = {
            "https://www.biznes-polska.pl/przetargi/dostawa-wag-samochodowych,123456/": """
            <html>
            <body>
                <h1>Dostawa wag samochodowych w roku 2026</h1>
                <p>Data dodania: 2026-07-25</p>
                <p>Opis: Szukamy wagi najazdowej.</p>
                <div class="contact-details">
                    <p>Dane kontaktowe: Jan Kowalski, tel. 555-666-777</p>
                </div>
            </body>
            </html>
            """
        }
        
        # Run scraper
        scraper = BiznesPolskaScraper()
        
        # Create a mock account with keywords
        class MockAccount:
            id = 123
            target_keywords = '["waga", "najazd"]'
            
        results = await scraper.fetch_leads(
            account=MockAccount(),
            start_date="2026-07-01",
            today_date="2026-07-26"
        )
        
        # Verify results
        self.assertEqual(len(results), 1)
        lead = results[0]
        self.assertEqual(lead["url"], "https://www.biznes-polska.pl/przetargi/dostawa-wag-samochodowych,123456/")
        self.assertIn("Jan Kowalski, tel. 555-666-777", lead["raw_text"])
        self.assertIn("Szukamy wagi najazdowej", lead["raw_text"])
        
        # Verify mock calls
        mock_fetch_multi.assert_called_once_with(
            ["https://www.biznes-polska.pl/przetargi/dostawa-wag-samochodowych,123456/"],
            "", "", "BiznesPolska"
        )


if __name__ == "__main__":
    unittest.main()
