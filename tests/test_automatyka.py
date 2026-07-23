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


if __name__ == "__main__":
    unittest.main()
