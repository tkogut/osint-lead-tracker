"""
tests/test_railway_seed.py — Weryfikacja automatycznego seedowania kampanii Wagi Kolejowe,
scalania CPV, zachowania słów kluczowych i idempotencji promptu.
"""

import json
import pytest
from sqlalchemy import select

from database import init_db, AsyncSessionLocal
from models import Account, PromptVersion
from seed import seed_data, RAILWAY_PROMPT, RAILWAY_KEYWORDS, RAILWAY_CPVS


@pytest.mark.asyncio
async def test_railway_campaign_seed_from_scratch(tmp_path, monkeypatch):
    test_db = tmp_path / "test_railway_scratch.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    import database
    import seed

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    # 1. Tworzenie konta "Wagi Kolejowe" od zera
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wagi Kolejowe").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.name == "Wagi Kolejowe"
        assert account.custom_prompt == RAILWAY_PROMPT
        assert json.loads(account.target_keywords) == RAILWAY_KEYWORDS
        assert json.loads(account.target_cpvs) == RAILWAY_CPVS
        assert account.llm_model == "gemini-2.5-flash"
        assert account.grounding_llm_model == "gemini-2.5-flash"
        assert account.llm_temperature == 0.1
        assert account.llm_max_tokens == 4096
        assert account.is_active is True

        sources = json.loads(account.enabled_sources)
        assert "BZP" in sources
        assert "Google" in sources
        assert "PlatformaZakupowa" in sources

        # Weryfikacja PromptVersion
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id).limit(1)
        )
        pv = pv_res.scalar_one_or_none()
        assert pv is not None
        assert pv.version == 1
        assert pv.prompt_text == RAILWAY_PROMPT


@pytest.mark.asyncio
async def test_railway_campaign_update_existing_preserves_keywords_and_merges_cpvs(tmp_path, monkeypatch):
    test_db = tmp_path / "test_railway_update.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    import database
    import seed

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    # Inicjalizacja bazy
    await database.init_db()

    # Pre-seed: konto o nazwie "Wagi Kolejowe" z własnymi słowami kluczowymi, starym promptem i częściowymi CPV
    custom_keywords = ["własne słowo 1", "unikalna fraza klienta", "waga torowa"]
    existing_cpvs = ["99999999-9", "42923110-6"]  # 42923110-6 jest w RAILWAY_CPVS, 99999999-9 jest customowe

    async with test_sessionmaker() as session:
        pre_account = Account(
            name="Wagi Kolejowe",
            target_cpvs=json.dumps(existing_cpvs),
            target_keywords=json.dumps(custom_keywords),
            custom_prompt="stary_inny_prompt",
            llm_model="gemini-2.5-flash",
            is_active=True
        )
        session.add(pre_account)
        await session.commit()

    # Uruchomienie seed_data - aktualizacja istniejącego konta
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wagi Kolejowe").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        # Prompt zaktualizowany
        assert account.custom_prompt == RAILWAY_PROMPT
        # Słowa kluczowe ZACHOWANE bez zmian
        assert json.loads(account.target_keywords) == custom_keywords
        # CPV scalone: zawiera 99999999-9 oraz wszystkie kody z RAILWAY_CPVS, bez duplikatów
        saved_cpvs = json.loads(account.target_cpvs)
        assert saved_cpvs[0] == "99999999-9"
        for cpv in RAILWAY_CPVS:
            assert cpv in saved_cpvs
        assert len(saved_cpvs) == len(set(saved_cpvs))
        assert len(saved_cpvs) == len(RAILWAY_CPVS) + 1  # 99999999-9 + 10 standardowych

        # PromptVersion utworzony
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) == 1
        assert pvs[0].version == 1
        assert pvs[0].prompt_text == RAILWAY_PROMPT

    # Ponowne uruchomienie seed_data dla sprawdzenia idempotencji
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wagi Kolejowe").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account.custom_prompt == RAILWAY_PROMPT
        assert json.loads(account.target_keywords) == custom_keywords
        assert json.loads(account.target_cpvs) == saved_cpvs

        # PromptVersion nadal 1 (brak duplikacji)
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) == 1


@pytest.mark.asyncio
async def test_railway_campaign_update_existing_singular_name(tmp_path, monkeypatch):
    """Test sprawdza rozpoznawanie konta o nazwie w liczbie pojedynczej ('Waga Kolejowa')."""
    test_db = tmp_path / "test_railway_singular.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    import database
    import seed

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    await database.init_db()

    custom_keywords = ["specyficzna waga bocznicowa"]
    async with test_sessionmaker() as session:
        pre_account = Account(
            name="Waga Kolejowa",
            target_cpvs=json.dumps(["42923110-6"]),
            target_keywords=json.dumps(custom_keywords),
            custom_prompt="stary_prompt_singular",
            llm_model="gemini-2.5-flash",
            is_active=True
        )
        session.add(pre_account)
        await session.commit()

    await seed_data()

    async with test_sessionmaker() as session:
        # Sprawdzamy, że nie utworzono drugiego konta "Wagi Kolejowe"
        all_railway = await session.execute(
            select(Account).filter(Account.name.in_(["Wagi Kolejowe", "Waga Kolejowa"]))
        )
        accounts = all_railway.scalars().all()
        assert len(accounts) == 1
        acc = accounts[0]
        assert acc.name == "Waga Kolejowa"
        assert acc.custom_prompt == RAILWAY_PROMPT
        assert json.loads(acc.target_keywords) == custom_keywords
        assert set(RAILWAY_CPVS).issubset(set(json.loads(acc.target_cpvs)))
