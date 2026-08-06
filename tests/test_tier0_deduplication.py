"""
test_tier0_deduplication.py — Testy jednostkowe dla funkcji deduplikacji Tier 0 w SQLite.
"""

import unittest
import asyncio
import os
import tempfile

import uuid
from database import init_db, is_url_visited, mark_url_visited


class TestTier0Deduplication(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Inicjalizacja tymczasowej bazy testowej
        await init_db()

    async def test_mark_and_check_visited_url(self):
        unique_id = uuid.uuid4().hex[:8]
        test_url = f"https://www.automatyka.pl/zapytania-ofertowe/waga-samochodowa-{unique_id}"
        account_id = 999
        source = "Automatyka"

        # 1. Sprawdzenie że URL nie był odwiedzony
        self.assertFalse(await is_url_visited(test_url, account_id))

        # 2. Oznaczenie URL jako odwiedzony
        await mark_url_visited(test_url, account_id, source, content_hash="hash123", status="PROCESSED")

        # 3. Sprawdzenie że URL jest teraz odwiedzony
        self.assertTrue(await is_url_visited(test_url, account_id))

        # 4. Sprawdzenie że URL dla innego konta nie wpływa na wyniki
        self.assertFalse(await is_url_visited(test_url, account_id + 1))

    async def test_lead_exists_logic(self):
        from database import lead_exists, AsyncSessionLocal
        from models import Lead, PromptVersion, Account
        import uuid
        from datetime import datetime

        unique_suffix = uuid.uuid4().hex[:8]
        test_title = f"Test Lead Title {unique_suffix}"
        test_url = f"https://example.com/unique-lead-url-path/{unique_suffix}"

        # 1. Non-existent lead
        self.assertFalse(await lead_exists(url=test_url, title=test_title, account_id=1))

        # Setup accounts, prompt version, and lead in DB
        async with AsyncSessionLocal() as session:
            acc1 = Account(name=f"Acc1-{unique_suffix}")
            acc2 = Account(name=f"Acc2-{unique_suffix}")
            session.add_all([acc1, acc2])
            await session.commit()

            acc1_id = acc1.id
            acc2_id = acc2.id

            pv1 = PromptVersion(account_id=acc1_id, version=1, prompt_text="Test prompt 1", created_at=datetime.utcnow())
            session.add(pv1)
            await session.commit()
            pv1_id = pv1.id

            lead1 = Lead(
                url=test_url,
                tytul=test_title,
                prompt_version_id=pv1_id,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead1)
            await session.commit()

        # 2. Querying by title (length > 5)
        # Matching account_id: should exist
        self.assertTrue(await lead_exists(url="", title=test_title, account_id=acc1_id))
        # Non-matching account_id: should not exist
        self.assertFalse(await lead_exists(url="", title=test_title, account_id=acc2_id))
        # None account_id: should exist
        self.assertTrue(await lead_exists(url="", title=test_title, account_id=None))

        # 3. Querying by url (length > 20 and not ending with domain suffix)
        # Matching account_id: should exist
        self.assertTrue(await lead_exists(url=test_url, title="", account_id=acc1_id))
        # Non-matching account_id: should not exist
        self.assertFalse(await lead_exists(url=test_url, title="", account_id=acc2_id))
        # None account_id: should exist
        self.assertTrue(await lead_exists(url=test_url, title="", account_id=None))

        # 4. Global lead (prompt_version_id is None)
        global_suffix = uuid.uuid4().hex[:8]
        global_title = f"Global Lead Title {global_suffix}"
        global_url = f"https://example.com/global-lead-url-path/{global_suffix}"

        async with AsyncSessionLocal() as session:
            lead_global = Lead(
                url=global_url,
                tytul=global_title,
                prompt_version_id=None,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(lead_global)
            await session.commit()

        # A global lead should match for any account_id (or None)
        self.assertTrue(await lead_exists(url="", title=global_title, account_id=acc1_id))
        self.assertTrue(await lead_exists(url="", title=global_title, account_id=acc2_id))
        self.assertTrue(await lead_exists(url=global_url, title="", account_id=acc1_id))
        self.assertTrue(await lead_exists(url=global_url, title="", account_id=acc2_id))


if __name__ == "__main__":
    unittest.main()
