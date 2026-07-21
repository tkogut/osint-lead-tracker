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


if __name__ == "__main__":
    unittest.main()
