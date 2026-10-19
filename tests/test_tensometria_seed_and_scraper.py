"""
tests/test_tensometria_seed_and_scraper.py — Weryfikacja automatycznego seedowania kampanii
Tensometria i Podzespoły Wagowe, scalania CPV i słów kluczowych, źródeł bez GUNB,
zgodności z format_prompt_dates oraz inteligentnego parsowania stron marek w AutomatykaScraper.
"""

import json
import pytest
from sqlalchemy import select

import database
import seed
from database import init_db, AsyncSessionLocal
from models import Account, PromptVersion
from seed import seed_data, TENSOMETRY_PROMPT, TENSOMETRY_KEYWORDS, TENSOMETRY_CPVS
from osint_engine import format_prompt_dates
from scrapers.automatyka import AutomatykaScraper, parse_notice_detail


@pytest.mark.asyncio
async def test_tensometria_campaign_seed_from_scratch(tmp_path, monkeypatch):
    test_db = tmp_path / "test_tenso_scratch.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    # Inicjalizacja bazy i seed_data
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Tensometria i Podzespoły Wagowe").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.name == "Tensometria i Podzespoły Wagowe"
        assert account.custom_prompt == TENSOMETRY_PROMPT
        assert json.loads(account.target_keywords) == TENSOMETRY_KEYWORDS
        assert json.loads(account.target_cpvs) == TENSOMETRY_CPVS
        assert account.llm_model == "gemini-2.5-flash"
        assert account.grounding_llm_model == "gemini-2.5-flash"
        assert account.llm_temperature == 0.1
        assert account.llm_max_tokens == 8192
        assert account.is_active is True

        sources = json.loads(account.enabled_sources)
        assert "GUNB" not in sources
        assert "BZP" in sources
        assert "Google" in sources
        assert "Automatyka" in sources
        assert "BazaKonkurencyjnosci" in sources
        assert "BiznesPolska" in sources
        assert "LoginTrade" in sources
        assert "PlatformaZakupowa" in sources

        # Weryfikacja PromptVersion
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id).limit(1)
        )
        pv = pv_res.scalar_one_or_none()
        assert pv is not None
        assert pv.version == 1
        assert pv.prompt_text == TENSOMETRY_PROMPT


@pytest.mark.asyncio
async def test_tensometria_campaign_update_existing_and_idempotency(tmp_path, monkeypatch):
    test_db = tmp_path / "test_tenso_update.db"
    test_db_url = f"sqlite:///{test_db}"
    test_async_url = f"sqlite+aiosqlite:///{test_db}"

    monkeypatch.setattr(database.settings, "sqlite_path", str(test_db))
    monkeypatch.setattr(database.settings, "database_url", test_db_url)

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    test_engine = create_async_engine(test_async_url, echo=False)
    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    monkeypatch.setattr(database, "async_engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", test_sessionmaker)
    monkeypatch.setattr(seed, "AsyncSessionLocal", test_sessionmaker)

    await database.init_db()

    # Pre-seed: konto o nazwie "Tensometria" z wcześniejszymi danymi i źródłem GUNB
    old_keywords = ["tensometr stary", "zemic"]
    existing_cpvs = ["99999999-9", "42923000-2"]
    old_sources = ["GUNB", "BZP", "Google"]

    async with test_sessionmaker() as session:
        pre_account = Account(
            name="Tensometria",
            target_cpvs=json.dumps(existing_cpvs),
            target_keywords=json.dumps(old_keywords),
            custom_prompt="stary_prompt_tensometria",
            llm_model="gemini-2.5-flash",
            grounding_llm_model="gemini-2.5-flash",
            llm_temperature=0.1,
            llm_max_tokens=4096,
            enabled_sources=json.dumps(old_sources),
            is_active=True
        )
        session.add(pre_account)
        await session.commit()

    # 1. Uruchomienie seed_data - aktualizacja istniejącego konta
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Tensometria").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.custom_prompt == TENSOMETRY_PROMPT
        assert account.llm_max_tokens == 8192

        # Słowa kluczowe scalone
        saved_kws = json.loads(account.target_keywords)
        assert "tensometr stary" in saved_kws
        for kw in TENSOMETRY_KEYWORDS:
            assert kw in saved_kws

        # CPV scalone
        saved_cpvs = json.loads(account.target_cpvs)
        assert "99999999-9" in saved_cpvs
        for cpv in TENSOMETRY_CPVS:
            assert cpv in saved_cpvs
        assert len(saved_cpvs) == len(set(saved_cpvs))

        # GUNB wykluczony
        sources = json.loads(account.enabled_sources)
        assert "GUNB" not in sources
        assert "Automatyka" in sources
        assert "BZP" in sources

        # PromptVersion utworzony/zaktualizowany
        pv_res = await session.execute(
            select(PromptVersion).filter(PromptVersion.account_id == account.id)
        )
        pvs = pv_res.scalars().all()
        assert len(pvs) >= 1
        assert pvs[-1].prompt_text == TENSOMETRY_PROMPT

    # 2. Sprawdzenie idempotencji
    await seed_data()

    async with test_sessionmaker() as session:
        result = await session.execute(
            select(Account).filter(Account.name == "Tensometria").limit(1)
        )
        account = result.scalar_one_or_none()
        assert account.custom_prompt == TENSOMETRY_PROMPT
        assert json.loads(account.target_cpvs) == saved_cpvs
        assert json.loads(account.target_keywords) == saved_kws


def test_automatyka_scraper_brand_page_parsing():
    """Weryfikuje precyzyjną ekstrakcję zapytania o tensometry z podstrony zbiorczej marki (topId)."""
    brand_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Zemic - zapytania ofertowe o markę</title></head>
    <body>
        <h1>Zemic - zapytania ofertowe o markę</h1>

        <div class="box-styles">
            <div class="box-meta">
                <span>Zapytanie nr 999123</span>
                <small>Opublikowano: 2021-05-10</small>
            </div>
            <h2>Stare zapytanie o czujniki Zemic z 2021 roku</h2>
            <div class="box-text">
                <div class="txt">To jest archiwalne zapytanie sprzed kilku lat, które nie powinno być ekstrahowane.</div>
            </div>
        </div>

        <div class="box-styles active">
            <div class="box-meta">
                <span>Zapytanie nr 1028693</span>
                <small>Opublikowano: 2026-10-16</small>
            </div>
            <h2>Tensometry Zemic</h2>
            <div class="box-text">
                <div class="txt">Dzień dobry, poszukujemy 8 sztuk belek tensometrycznych Zemic H8C 2t wraz z puszką sumującą.</div>
            </div>
        </div>

        <div class="box-styles">
            <div class="box-meta">
                <span>Zapytanie nr 888456</span>
                <small>Opublikowano: 2019-02-15</small>
            </div>
            <h2>Inne zapytanie Zemic</h2>
            <div class="box-text">
                <div class="txt">Kolejne stare zapytanie.</div>
            </div>
        </div>
    </body>
    </html>
    """

    # Parsowanie z podaniem URL zawierającego topId
    detail_url = "https://www.automatyka.pl/zapytania-ofertowe/zemic-27?topId=1028693"
    parsed = AutomatykaScraper.parse_notice_detail(brand_html, detail_url)

    assert parsed["title"] == "Tensometry Zemic"
    assert parsed["pub_date_str"] == "2026-10-16"
    assert "Tensometry Zemic" in parsed["clean_text"]
    assert "Zemic H8C" in parsed["clean_text"]
    assert "Stare zapytanie o czujniki Zemic" not in parsed["clean_text"]
    assert "Inne zapytanie Zemic" not in parsed["clean_text"]


def test_automatyka_scraper_standard_notice_parsing():
    """Weryfikuje standardowe parsowanie pojedynczego ogłoszenia bez box-styles."""
    standard_html = """
    <html>
    <body>
        <h1>Przetworniki wagowe i miernik wagowy Dini Argeo</h1>
        <p>Opublikowano: 2026-10-15</p>
        <div>Dostawa miernika Dini Argeo DFWLB oraz 4 czujników belkowych do wagi zbiornikowej.</div>
    </body>
    </html>
    """
    detail_url = "https://www.automatyka.pl/zapytania-ofertowe/przetworniki-wagowe-12345-67"
    parsed = parse_notice_detail(standard_html, detail_url)

    assert parsed["title"] == "Przetworniki wagowe i miernik wagowy Dini Argeo"
    assert parsed["pub_date_str"] == "2026-10-15"
    assert "Dini Argeo" in parsed["clean_text"]


def test_tensometria_prompt_format_prompt_dates_compatibility():
    """Weryfikuje kompatybilność TENSOMETRY_PROMPT z dynamicznym zastępowaniem dat."""
    today = "2026-10-25"
    start = "2026-10-18"

    formatted = format_prompt_dates(TENSOMETRY_PROMPT, today, start)

    # Weryfikacja zastąpienia bieżącej daty
    assert f"Dzisiejsza data (rok 2026) to: {today}." in formatted
    # Weryfikacja zastąpienia okna czasowego
    assert f"od {start} do {today}." in formatted
    # Upewnienie się, że pierwotne sztywne daty z szablonu zostały podmienione
    assert "od 2026-10-04 do 2026-10-11" not in formatted
