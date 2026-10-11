"""
test_deduplication.py — Testy jednostkowe dla PLAN-063:
Global Lead Deduplication, Containment Title Matching, BZP Extraction & Odoo Safeguards.
"""

import unittest
import uuid
from datetime import datetime
from sqlalchemy import select

from database import (
    init_db,
    normalize_title,
    is_title_duplicate,
    lead_exists,
    update_lead_odoo_id,
    AsyncSessionLocal,
)
from models import Lead, PromptVersion, Account


class TestTitleDeduplicationContainment(unittest.TestCase):
    def test_is_title_duplicate_exact(self):
        t1 = "Dostawa i montaż stacji transformatorowej"
        t2 = "Dostawa i montaż stacji transformatorowej"
        self.assertTrue(is_title_duplicate(t1, t2))

    def test_is_title_duplicate_jaccard_70(self):
        # 10 words vs 7 common tokens: union = 10, intersection = 7 -> 70%
        # e.g.:
        # t1: "modernizacja oczyszczalni sciekow w miejscowosci kowale etap pierwszy zadanie a" (10 words)
        # t2: "modernizacja oczyszczalni sciekow w miejscowosci kowale etap pierwszy" (8 words)
        # intersection = 8, union = 10 -> 80% >= 70%
        t1 = "modernizacja oczyszczalni ścieków w miejscowości kowale etap pierwszy zadanie a"
        t2 = "modernizacja oczyszczalni ścieków w miejscowości kowale etap pierwszy"
        self.assertTrue(is_title_duplicate(t1, t2))

    def test_is_title_duplicate_containment_gwda(self):
        # GWDA case: short title vs long title with investor address
        # t1: krótki tytuł z portalu (np. BiznesPolska)
        # t2: długi tytuł z BZP/e-Zamówienia zawierający dokładny adres zamawiającego
        t1 = "Przegląd i serwis instalacji technologicznych na terenie oczyszczalni ścieków GWDA w Pile"
        t2 = "Przegląd i serwis instalacji technologicznych na terenie oczyszczalni ścieków GWDA w Pile przy ul Na Leszkowie 4 64 920 Piła"
        self.assertTrue(is_title_duplicate(t1, t2))

    def test_is_title_duplicate_different_locations_negative(self):
        t1 = "Budowa sieci kanalizacyjnej i pompowni ścieków w miejscowości Poznań"
        t2 = "Dostawa sprzętu komputerowego i serwerów dla Urzędu Miasta Wrocław"
        self.assertFalse(is_title_duplicate(t1, t2))


class TestGlobalLeadExists(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

    async def test_cross_account_url_deduplication(self):
        unique_suffix = uuid.uuid4().hex[:8]
        shared_url = f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/2026-BZP-{unique_suffix}-01"
        title1 = f"Tytuł postępowania pierwszego {unique_suffix}"
        title2 = f"Tytuł postępowania drugiego {unique_suffix}"

        async with AsyncSessionLocal() as session:
            acc1 = Account(name=f"AccA-{unique_suffix}")
            acc2 = Account(name=f"AccB-{unique_suffix}")
            session.add_all([acc1, acc2])
            await session.commit()
            acc1_id, acc2_id = acc1.id, acc2.id

            pv1 = PromptVersion(account_id=acc1_id, version=1, prompt_text="Test 1", created_at=datetime.utcnow())
            session.add(pv1)
            await session.commit()

            lead = Lead(
                url=shared_url,
                tytul=title1,
                prompt_version_id=pv1.id,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead)
            await session.commit()

        # Sprawdzamy czy dla konta acc2 ten URL jest wykrywany jako duplikat (Global URL dedup)
        exists_acc2 = await lead_exists(url=shared_url, title=title2, account_id=acc2_id)
        self.assertTrue(exists_acc2, "URL powinien zostać wykryty jako duplikat globalnie, nawet dla innego account_id")

    async def test_bzp_notice_number_extraction(self):
        unique_num = f"{uuid.uuid4().int % 90000000 + 10000000}"  # 8 cyfr
        unique_suffix = uuid.uuid4().hex[:6]
        url_in_db = f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/{unique_num}/szczegoly"
        url_incoming = f"https://bzp.uzp.gov.pl/notice-details/{unique_num}?ref=portal_{unique_suffix}"

        async with AsyncSessionLocal() as session:
            acc = Account(name=f"AccBZP-{unique_suffix}")
            session.add(acc)
            await session.commit()

            lead = Lead(
                url=url_in_db,
                tytul=f"Ogłoszenie przetargowe BZP {unique_num}",
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead)
            await session.commit()
            acc_id = acc.id

        exists_bzp = await lead_exists(url=url_incoming, title="Inny tytuł z agregatora", account_id=acc_id)
        self.assertTrue(exists_bzp, "Powinno wykryć duplikat po numerze ogłoszenia BZP w URL")

    async def test_update_lead_odoo_id(self):
        unique_suffix = uuid.uuid4().hex[:8]
        test_url = f"https://example.com/tender-odoo-test-{unique_suffix}"

        async with AsyncSessionLocal() as session:
            lead = Lead(
                url=test_url,
                tytul=f"Test Odoo update {unique_suffix}",
                odoo_id=None,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead)
            await session.commit()
            lead_id = lead.id

        # Wywołujemy update_lead_odoo_id
        await update_lead_odoo_id(lead_id, 45678)

        # Sprawdzamy stan w bazie
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Lead).filter(Lead.id == lead_id).limit(1))
            updated_lead = res.scalar_one_or_none()
            self.assertIsNotNone(updated_lead)
            self.assertEqual(updated_lead.odoo_id, 45678)


if __name__ == "__main__":
    unittest.main()
