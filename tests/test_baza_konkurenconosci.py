"""
test_baza_konkurenconosci.py — Testy jednostkowe dla wtyczki Baza Konkurencyjności.
"""

import unittest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.baza_konkurenconosci import BazaKonkurenconosciScraper


class TestBazaKonkurenconosciScraperAsync(unittest.IsolatedAsyncioTestCase):
    @patch("scrapers.baza_konkurenconosci.AsyncSession")
    @patch("scrapers.baza_konkurenconosci.is_url_visited")
    @patch("scrapers.baza_konkurenconosci.mark_url_visited")
    async def test_fetch_leads_success(self, mock_mark_visited, mock_is_visited, mock_session_cls):
        # 1. Setup mock database answers
        mock_is_visited.return_value = False
        
        # 2. Setup mock session (curl_cffi)
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mock search list response
        mock_list_resp = MagicMock()
        mock_list_resp.status_code = 200
        mock_list_resp.json.return_value = {
            "data": {
                "advertisements": [
                    {
                        "id": 12345,
                        "publication_date": "2026-07-26",
                        "title": "Dostawa wagi samochodowej w Gminie X",
                        "content": "Szukamy wagi najazdowej."
                    }
                ]
            }
        }
        
        # Mock detail response
        mock_detail_resp = MagicMock()
        mock_detail_resp.status_code = 200
        mock_detail_resp.json.return_value = {
            "data": {
                "advertisement": {
                    "id": 12345,
                    "title": "Dostawa wagi samochodowej w Gminie X",
                    "contact_persons": [
                        {
                            "forename": "Jan",
                            "surname": "Kowalski",
                            "phone_number": "555-666-777",
                            "email": "jkowalski@gminax.pl"
                        }
                    ],
                    "orders": [
                        {
                            "order_items": [
                                {
                                    "description": "Zadanie 1: Dostawa i montaż wagi 60t."
                                }
                            ]
                        }
                    ]
                }
            }
        }
        
        # Mocking list response and detail response. The loop iterates 10 pages,
        # so we will provide empty lists for the subsequent page requests.
        mock_empty_list = MagicMock()
        mock_empty_list.status_code = 200
        mock_empty_list.json.return_value = {"data": {"advertisements": []}}
        
        responses = [mock_list_resp, mock_detail_resp] + [mock_empty_list] * 9
        mock_session.get.side_effect = responses
        
        # 3. Create mock account and run scraper
        class MockAccount:
            id = 999
            target_keywords = json.dumps(["waga", "najazd"])
            
        scraper = BazaKonkurenconosciScraper()
        leads = await scraper.fetch_leads(
            account=MockAccount(),
            start_date="2026-07-01",
            today_date="2026-07-26"
        )
        
        # Verify results
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual(lead["url"], "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/12345")
        self.assertEqual(lead["tytul"], "Dostawa wagi samochodowej w Gminie X")
        self.assertIn("Jan Kowalski", lead["raw_text"])
        self.assertIn("jkowalski@gminax.pl", lead["raw_text"])
        self.assertIn("Dostawa i montaż wagi 60t", lead["raw_text"])


if __name__ == "__main__":
    unittest.main()
