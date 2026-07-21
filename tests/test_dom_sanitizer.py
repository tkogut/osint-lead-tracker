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


if __name__ == "__main__":
    unittest.main()
