"""
test_lead_deduplication.py — Testy jednostkowe dla inteligentnej normalizacji tytułów
i wieloźródłowej deduplikacji leadów (Plan 048).
"""

import unittest
import uuid
from datetime import datetime
from database import init_db, normalize_title, is_title_duplicate, lead_exists, AsyncSessionLocal
from models import Lead, PromptVersion, Account


class TestTitleNormalizationAndDuplicate(unittest.TestCase):
    def test_normalize_title_basic(self):
        self.assertEqual(normalize_title(""), "")
        self.assertEqual(normalize_title("   "), "")
        self.assertEqual(normalize_title("Budowa drogi"), "budowa drogi")

    def test_normalize_title_quotes_and_dashes(self):
        # Polish typographic quotes „ ”, english “ ”, guillemets « », apostrophes
        raw = "„Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu – etap II”"
        expected = "kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w podegrodziu etap ii"
        self.assertEqual(normalize_title(raw), expected)

        raw_straight = '"Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu - etap II"'
        self.assertEqual(normalize_title(raw_straight), expected)

        raw_guillemets = "«Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu — etap II»"
        self.assertEqual(normalize_title(raw_guillemets), expected)

    def test_normalize_title_punctuation_and_whitespace(self):
        raw = "   Dostawa   aparatury medycznej:   (Zadanie nr 1 / Tom A)...   "
        expected = "dostawa aparatury medycznej zadanie nr 1 tom a"
        self.assertEqual(normalize_title(raw), expected)

    def test_is_title_duplicate_exact_and_normalized(self):
        t1 = "„Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu – etap II”"
        t2 = "Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu - etap II"
        self.assertTrue(is_title_duplicate(t1, t2))

    def test_is_title_duplicate_token_overlap(self):
        # 10 words base vs 11 words with 1 extra word ("przetarg") -> Jaccard 10/11 = 90.9% >= 85%
        t1 = "Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu etap II"
        t2 = "Kompleksowa modernizacja i rozbudowa oczyszczalni ścieków w Podegrodziu etap II przetarg"
        self.assertTrue(is_title_duplicate(t1, t2))

    def test_is_title_duplicate_different_tenders_negative(self):
        # Distinct localities: overlap < 85%
        t1 = "Budowa sieci wodociągowej i kanalizacyjnej w miejscowości Kowale"
        t2 = "Budowa sieci wodociągowej i kanalizacyjnej w miejscowości Gdańsk"
        self.assertFalse(is_title_duplicate(t1, t2))

        # Different stages (etap 1 vs etap 2)
        t3 = "Modernizacja oświetlenia ulicznego na terenie Gminy Wieliczka - etap 1"
        t4 = "Modernizacja oświetlenia ulicznego na terenie Gminy Wieliczka - etap 2"
        self.assertFalse(is_title_duplicate(t3, t4))

    def test_is_title_duplicate_short_titles(self):
        # Short titles (< 4 words) require exact normalized match
        self.assertTrue(is_title_duplicate("Waga samochodowa", "„Waga samochodowa”"))
        self.assertFalse(is_title_duplicate("Waga samochodowa 1", "Waga samochodowa 2"))


class TestLeadExistsSmartDeduplication(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

    async def test_cross_source_title_deduplication(self):
        unique_suffix = uuid.uuid4().hex[:8]
        bzp_title = f"„Kompleksowa modernizacja oczyszczalni ścieków w Gminie Testowej {unique_suffix} – etap I”"
        aggregator_title = f"Kompleksowa modernizacja oczyszczalni ścieków w Gminie Testowej {unique_suffix} - etap I"
        
        bzp_url = f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/{unique_suffix}"
        aggregator_url = f"https://tendario.pl/przetargi/ogloszenie-{unique_suffix}"

        # 1. Setup account and insert BZP lead
        async with AsyncSessionLocal() as session:
            acc = Account(name=f"DedupAcc-{unique_suffix}")
            session.add(acc)
            await session.commit()
            acc_id = acc.id

            pv = PromptVersion(account_id=acc_id, version=1, prompt_text="Dedup test", created_at=datetime.utcnow())
            session.add(pv)
            await session.commit()
            pv_id = pv.id

            lead = Lead(
                url=bzp_url,
                tytul=bzp_title,
                prompt_version_id=pv_id,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead)
            await session.commit()

        # 2. Check aggregator lead with different URL but matching normalized title
        exists = await lead_exists(url=aggregator_url, title=aggregator_title, account_id=acc_id)
        self.assertTrue(exists)

        # 3. Check different tender title for same account does not falsely match
        different_title = f"Budowa nowej drogi gminnej w Gminie Innej {unique_suffix}"
        exists_diff = await lead_exists(url=aggregator_url, title=different_title, account_id=acc_id)
        self.assertFalse(exists_diff)

        # 4. Check account isolation
        other_acc_id = acc_id + 999
        exists_other_acc = await lead_exists(url=aggregator_url, title=aggregator_title, account_id=other_acc_id)
        self.assertFalse(exists_other_acc)


if __name__ == "__main__":
    unittest.main()
