"""
test_dom_sanitizer.py — Testy jednostkowe dla klasy DOMSanitizer.
"""

import unittest
from scrapers.base import DOMSanitizer


class TestDOMSanitizer(unittest.TestCase):
    def test_clean_empty_html(self):
        self.assertEqual(DOMSanitizer.clean(""), "")
        self.assertEqual(DOMSanitizer.clean("   "), "")

    def test_clean_html_strips_scripts_and_nav(self):
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log("secret tracker");</script>
        </head>
        <body>
            <header><nav><a href="/home">Strona główna</a></nav></header>
            <main>
                <article>
                    <h1>Zapytanie Ofertowe: Waga Samochodowa 60t</h1>
                    <p>Zamawiający ogłasza przetarg na dostawę wagi samochodowej najazdowej 60-tonowej w Poznaniu.</p>
                </article>
            </main>
            <footer><p>Copyright 2026 Portal Ofertowy</p></footer>
        </body>
        </html>
        """
        clean_text = DOMSanitizer.clean(sample_html)
        self.assertIn("Zapytanie Ofertowe", clean_text)
        self.assertIn("60-tonowej", clean_text)
        self.assertNotIn("console.log", clean_text)
        self.assertNotIn("color: red", clean_text)

    def test_clean_html_max_chars_limit(self):
        long_html = "<html><body>" + "<p>Waga samochodowa. </p>" * 500 + "</body></html>"
        clean_text = DOMSanitizer.clean(long_html, max_chars=100)
        self.assertLessEqual(len(clean_text), 100)

    def test_clean_logintrade_boilerplate(self):
        sample_html = """
        <html>
        <body>
            <p>Treść zapytania o wagę samochodową 60t.</p>
            <div>Enquiry is out of date.</div>
            <div>Time to make an offer is up...</div>
            <div>The Purchasing Platform Terms of Use are available in the registration panel.</div>
            <div>Registering in our company suppliers base, receiving enquiries and making sales offers are free of charge.</div>
            <div>To browse enquiries from a given company, you must be registered in their suppliers database.</div>
        </body>
        </html>
        """
        clean_text = DOMSanitizer.clean(sample_html)
        self.assertIn("Treść zapytania o wagę samochodową 60t.", clean_text)
        self.assertNotIn("Enquiry is out of date", clean_text)
        self.assertNotIn("Time to make an offer is up", clean_text)
        self.assertNotIn("Purchasing Platform Terms of Use", clean_text)
        self.assertNotIn("Registering in our company suppliers base", clean_text)
        self.assertNotIn("To browse enquiries from a given company", clean_text)


if __name__ == "__main__":
    unittest.main()
