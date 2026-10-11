"""
tests/test_calibration_seed.py — Weryfikacja automatycznego seedowania kampanii
Wzorcowanie Wag i Wzorców Masy, scalania CPV, aktualizacji słów kluczowych,
idempotencji i zgodności z format_prompt_dates.
"""

import json
import pytest
from sqlalchemy import select

from database import init_db, AsyncSessionLocal
from models import Account, PromptVersion
from seed import seed_data, CALIBRATION_PROMPT, CALIBRATION_KEYWORDS, CALIBRATION_CPVS
from osint_engine import format_prompt_dates


@pytest.mark.asyncio
async def test_calibration_campaign_seed_from_scratch(tmp_path, monkeypatch):
    test_db = tmp_path / "test_calibration_scratch.db"
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

    # 1. Tworzenie konta "Wzorcowanie Wag i Wzorców Masy" od zera
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wzorcowanie Wag i Wzorców Masy").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.name == "Wzorcowanie Wag i Wzorców Masy"
        assert account.custom_prompt == CALIBRATION_PROMPT
        assert json.loads(account.target_keywords) == CALIBRATION_KEYWORDS
        assert json.loads(account.target_cpvs) == CALIBRATION_CPVS
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
        assert pv.prompt_text == CALIBRATION_PROMPT


@pytest.mark.asyncio
async def test_calibration_campaign_update_existing_and_idempotency(tmp_path, monkeypatch):
    test_db = tmp_path / "test_calibration_update.db"
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

    # Pre-seed: konto o nazwie "Wzorcowanie Wag" ze starymi danymi
    old_keywords = ["wzorcowanie", "kalibracja", "waga"]
    existing_cpvs = ["99999999-9", "50433000-9"]

    async with test_sessionmaker() as session:
        pre_account = Account(
            name="Wzorcowanie Wag",
            target_cpvs=json.dumps(existing_cpvs),
            target_keywords=json.dumps(old_keywords),
            custom_prompt="stary_prompt_wzorcowanie",
            llm_model="gemini-2.5-flash",
            is_active=True
        )
        session.add(pre_account)
        await session.commit()

    # 1. Uruchomienie seed_data - aktualizacja istniejącego konta
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wzorcowanie Wag").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        # Prompt zaktualizowany
        assert account.custom_prompt == CALIBRATION_PROMPT
        # Słowa kluczowe zaktualizowane do CALIBRATION_KEYWORDS
        assert json.loads(account.target_keywords) == CALIBRATION_KEYWORDS
        # CPV scalone z CALIBRATION_CPVS bez duplikatów
        saved_cpvs = json.loads(account.target_cpvs)
        assert saved_cpvs[0] == "99999999-9"
        for cpv in CALIBRATION_CPVS:
            assert cpv in saved_cpvs
        assert len(saved_cpvs) == len(set(saved_cpvs))
        assert len(saved_cpvs) == len(CALIBRATION_CPVS) + 1

        # PromptVersion utworzony
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) == 1
        assert pvs[0].version == 1
        assert pvs[0].prompt_text == CALIBRATION_PROMPT

    # 2. Ponowne uruchomienie seed_data dla sprawdzenia idempotencji
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Wzorcowanie Wag").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account.custom_prompt == CALIBRATION_PROMPT
        assert json.loads(account.target_keywords) == CALIBRATION_KEYWORDS
        assert json.loads(account.target_cpvs) == saved_cpvs

        # PromptVersion nadal 1 (brak duplikacji)
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) == 1


def test_calibration_prompt_format_prompt_dates_compatibility():
    """Weryfikuje kompatybilność CALIBRATION_PROMPT z dynamicznym zastępowaniem dat."""
    today = "2026-10-25"
    start = "2026-10-18"

    formatted = format_prompt_dates(CALIBRATION_PROMPT, today, start)

    # Weryfikacja zastąpienia bieżącej daty
    assert f"Dzisiejsza data (rok 2026) to: {today}." in formatted
    # Weryfikacja zastąpienia okna czasowego
    assert f"od {start} do {today}." in formatted
    # Upewnienie się, że pierwotne sztywne daty z szablonu zostały podmienione
    assert "od 2026-10-04 do 2026-10-11" not in formatted
