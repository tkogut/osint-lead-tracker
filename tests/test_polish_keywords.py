"""
test_polish_keywords.py — Testy jednostkowe dla match_polish_keywords w utils.py.
"""

import unittest
from src.utils import match_polish_keywords

class TestPolishKeywords(unittest.TestCase):
    def test_empty_keywords_returns_true(self):
        self.assertTrue(match_polish_keywords("Dowolny tekst", []))
        self.assertTrue(match_polish_keywords("Dowolny tekst", [None]))
        self.assertTrue(match_polish_keywords("Dowolny tekst", [""]))

    def test_simple_exact_match(self):
        self.assertTrue(match_polish_keywords("Kolejowa waga samochodowa", ["waga"]))
        self.assertTrue(match_polish_keywords("Kolejowa waga samochodowa", ["WAGA"]))
        self.assertTrue(match_polish_keywords("Kolejowa waga samochodowa", ["  waga  "]))
        self.assertFalse(match_polish_keywords("Kolejowa waga samochodowa", ["najazdowa"]))

    def test_polish_grammar_inflections(self):
        # 'waga' stem is 'wag', 'samochodowa' stem is 'samochodow'
        # 'wag' and 'samochodow' are both in 'dostawa wag samochodowych'
        self.assertTrue(match_polish_keywords("dostawa wag samochodowych", ["waga samochodowa"]))
        
        # 'wagi' stem is 'wag', 'samochodowej' stem is 'samochodow'
        self.assertTrue(match_polish_keywords("Zakup wagi samochodowej w Gdyni", ["waga samochodowa"]))

    def test_stem_od_replacement(self):
        # 'samochód' stem is 'samochod' after 'ód' -> 'od' rule
        # 'samochod' is in 'samochodów'
        self.assertTrue(match_polish_keywords("zakup samochodów", ["samochód"]))

    def test_stem_t_removal(self):
        # 'wiertarka' -> 'wiertark' -> ends in 't'? No, 'wiertarka' stem is 'wiertark'.
        # Let's use word ending in 't' like 'asfalt'. 'asfalt' stem is 'asfal' (since it ends in 't').
        # 'asfal' is in 'asfaltu'
        self.assertTrue(match_polish_keywords("wylanie asfaltu", ["asfalt"]))

    def test_multi_word_distance_window(self):
        # Keywords: 'waga samochodowa' -> stems: 'wag', 'samochodow'
        # If 'wag' and 'samochodow' are far apart, they should not match
        text_far = "wag ... " + ("x" * 150) + " ... samochodowych"
        self.assertFalse(match_polish_keywords(text_far, ["waga samochodowa"]))
        
        text_near = "wag ... " + ("x" * 30) + " ... samochodowych"
        self.assertTrue(match_polish_keywords(text_near, ["waga samochodowa"]))
