"""
tests/test_agro_seed.py — Weryfikacja automatycznego seedowania kampanii Agro i wersji promptu.
"""

import json
import pytest
from sqlalchemy import select

from database import init_db, AsyncSessionLocal
from models import Account, PromptVersion
from seed import seed_data, AGRO_PROMPT, AGRO_KEYWORDS, AGRO_CPVS


@pytest.mark.asyncio
async def test_agro_campaign_seed_and_update(tmp_path, monkeypatch):
    test_db = tmp_path / "test_agro.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    import database
    import config

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)
    
    # Podmiana silnika dla testu
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    import seed
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    # 1. Pierwsze uruchomienie seed_data (tworzenie od zera)
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(select(Account).filter(Account.name == "Agro").limit(1))
        agro_account = result.scalar_one_or_none()
        assert agro_account is not None
        assert agro_account.name == "Agro"
        assert agro_account.custom_prompt == AGRO_PROMPT
        assert json.loads(agro_account.target_keywords) == AGRO_KEYWORDS
        assert json.loads(agro_account.target_cpvs) == AGRO_CPVS
        assert agro_account.llm_model == "gemini-2.5-flash"
        assert agro_account.grounding_llm_model == "gemini-2.5-flash"
        assert agro_account.llm_temperature == 0.1
        assert agro_account.llm_max_tokens == 4096
        assert agro_account.is_active is True
        
        sources = json.loads(agro_account.enabled_sources)
        assert "BZP" in sources
        assert "Google" in sources
        assert "PlatformaZakupowa" in sources

        # Sprawdzenie PromptVersion
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == agro_account.id).limit(1)
        )
        pv = pv_res.scalar_one_or_none()
        assert pv is not None
        assert pv.version == 1
        assert pv.prompt_text == AGRO_PROMPT

    # 2. Drugie uruchomienie seed_data (aktualizacja / idempotencja)
    # Zmieniamy tymczasowo custom_prompt, żeby sprawdzić czy seed go przywróci/zaktualizuje
    async with test_sessionmaker() as session:
        result = await session.execute(select(Account).filter(Account.name == "Agro").limit(1))
        agro_account = result.scalar_one_or_none()
        agro_account.custom_prompt = "stary_prompt"
        agro_account.target_keywords = json.dumps(["stare_slowo"])
        await session.commit()

    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(select(Account).filter(Account.name == "Agro").limit(1))
        agro_account = result.scalar_one_or_none()
        assert agro_account.custom_prompt == AGRO_PROMPT
        assert json.loads(agro_account.target_keywords) == AGRO_KEYWORDS
        assert json.loads(agro_account.target_cpvs) == AGRO_CPVS

        # Sprawdzenie czy nie zduplikowano PromptVersion
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == agro_account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) == 1
        assert pvs[0].prompt_text == AGRO_PROMPT
