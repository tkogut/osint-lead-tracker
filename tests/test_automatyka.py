"""
test_automatyka.py — Testy jednostkowe dla automatyka.py
"""

import unittest
from scrapers.automatyka import extract_advertiser_info


class TestAutomatykaScraper(unittest.TestCase):
    def test_extract_advertiser_info_found(self):
        html_content = """
        <html>
        <body>
            <section class="contact-details">
                <h2>Dane kontaktowe</h2>
                <p>Firma: Testowa Firma Sp. z o.o.</p>
                <p>Osoba kontaktowa: Jan Kowalski</p>
                <p>E-mail: kontakt@test.pl</p>
                <p>Telefon: +48 123 456 789</p>
                <p>Adres: ul. Testowa 1, Warszawa</p>
            </section>
        </body>
        </html>
        """
        result = extract_advertiser_info(html_content)
        self.assertIn("=== DANE OGŁASZAJĄCEGO ===", result)
        self.assertIn("Nazwa firmy: Testowa Firma Sp. z o.o.", result)
        self.assertIn("Osoba kontaktowa: Jan Kowalski", result)
        self.assertIn("Adres e-mail: kontakt@test.pl", result)
        self.assertIn("Nr telefonu: +48 123 456 789", result)
        self.assertIn("Adres do kontaktu: ul. Testowa 1, Warszawa", result)

    def test_extract_advertiser_info_not_found(self):
        html_content = """
        <html>
        <body>
            <p>Brak sekcji z danymi kontaktowymi.</p>
        </body>
        </html>
        """
        result = extract_advertiser_info(html_content)
        self.assertEqual(result, "")


from unittest.mock import patch, AsyncMock
from scrapers.automatyka import AutomatykaScraper


class TestAutomatykaScraperAsync(unittest.IsolatedAsyncioTestCase):
    @patch("scrapers.automatyka.AsyncSession")
    @patch("scrapers.automatyka.fetch_multiple_with_playwright")
    @patch("scrapers.automatyka.is_url_visited")
    @patch("scrapers.automatyka.mark_url_visited")
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
            <a href="/zapytania-ofertowe/waga-samochodowa-1-2">Szczegóły</a>
        </body>
        </html>
        """
        
        # Mock detail page response (Phase 1)
        mock_detail_resp = AsyncMock()
        mock_detail_resp.status_code = 200
        mock_detail_resp.text = """
        <html>
        <body>
            <h1>Waga samochodowa 60t</h1>
            <p>Opublikowano: 2026-07-25</p>
            <p>Szukamy wagi najazdowej dla fabryki.</p>
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
            "https://www.automatyka.pl/zapytania-ofertowe/waga-samochodowa-1-2": """
            <html>
            <body>
                <section class="contact-details">
                    <h2>Dane kontaktowe</h2>
                    <p>Firma: Przykładowy Klient</p>
                    <p>E-mail: biuro@klient.pl</p>
                </section>
            </body>
            </html>
            """
        }
        
        # Run scraper
        scraper = AutomatykaScraper()
        
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
        self.assertEqual(lead["url"], "https://www.automatyka.pl/zapytania-ofertowe/waga-samochodowa-1-2")
        self.assertIn("Nazwa firmy: Przykładowy Klient", lead["raw_text"])
        self.assertIn("biuro@klient.pl", lead["raw_text"])
        self.assertIn("Szukamy wagi najazdowej", lead["raw_text"])
        
        # Verify mock calls
        mock_fetch_multi.assert_called_once_with(
            ["https://www.automatyka.pl/zapytania-ofertowe/waga-samochodowa-1-2"],
            "", "", "Automatyka"
        )


if __name__ == "__main__":
    unittest.main()
