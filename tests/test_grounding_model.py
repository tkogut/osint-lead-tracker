"""
tests/test_grounding_model.py — Testy jednostkowe dla dedykowanego selektora modeli Gemini
dla Google Search Grounding w kontach (Plan 057 / Issue #3).
"""

import pytest
import sqlite3
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock

from models import Account, Base
from schemas import AccountCreate, AccountResponse
from src.osint_engine import OSINTEngine
from src.llm_client import LLMResult
from main import app, get_current_user
from models import User
from database import init_db
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    import asyncio
    os.makedirs("./data", exist_ok=True)
    asyncio.run(init_db())


async def override_current_user():
    return User(id=1, username="admin", role="admin")


@pytest.fixture
def setup_auth():
    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_account_model_grounding_llm_model_field():
    """Weryfikuje pole grounding_llm_model w modelu SQLAlchemy Account."""
    # Sprawdzenie definicji kolumny i jej domyślnej wartości w schemacie SQLAlchemy
    assert Account.grounding_llm_model.default.arg == "gemini-2.5-flash"
    assert Account.grounding_llm_model.nullable is False

    acc = Account(
        name="Test Grounding Campaign",
        target_cpvs='["42923110-6"]',
        target_keywords='["wagi"]',
        grounding_llm_model="gemini-2.5-pro"
    )
    assert acc.grounding_llm_model == "gemini-2.5-pro"


def test_schemas_grounding_llm_model():
    """Weryfikuje walidację w AccountCreate i AccountResponse."""
    create_schema = AccountCreate(
        name="Nowa Kampania",
        target_cpvs=["42923110-6"],
        target_keywords=["waga"],
        llm_model="anthropic/claude-3.7-sonnet",
        grounding_llm_model="gemini-2.5-pro"
    )
    assert create_schema.llm_model == "anthropic/claude-3.7-sonnet"
    assert create_schema.grounding_llm_model == "gemini-2.5-pro"

    # Wartość domyślna
    default_schema = AccountCreate(
        name="Kampania Domyślna",
        target_cpvs=[],
        target_keywords=[]
    )
    assert default_schema.grounding_llm_model == "gemini-2.5-flash"

    # Response schema
    response_schema = AccountResponse(
        id=1,
        name="Kampania Response",
        target_cpvs=[],
        target_keywords=[],
        enabled_sources=["Google"],
        custom_prompt=None,
        llm_model="deepseek/deepseek-chat",
        grounding_llm_model="gemini-2.0-flash",
        llm_temperature=0.2,
        llm_max_tokens=2048,
        odoo_company_id=None,
        odoo_user_id=None,
        odoo_tag_ids=[],
        odoo_team_id=None,
        odoo_source_id=None,
        is_active=True
    )
    assert response_schema.grounding_llm_model == "gemini-2.0-flash"


def test_idempotent_sqlite_migration(tmp_path):
    """Weryfikuje idempotentną migrację bazy SQLite za pomocą PRAGMA table_info."""
    db_file = tmp_path / "test_migration.db"
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    # Tworzymy tabelę accounts bez kolumny grounding_llm_model
    cur.execute("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE NOT NULL,
            target_cpvs TEXT NOT NULL DEFAULT '[]',
            target_keywords TEXT NOT NULL DEFAULT '[]',
            enabled_sources TEXT NOT NULL DEFAULT '["BZP", "Google", "GUNB"]',
            custom_prompt TEXT,
            llm_model VARCHAR(100) NOT NULL DEFAULT 'gemini-2.5-flash',
            llm_temperature FLOAT NOT NULL DEFAULT 0.1,
            llm_max_tokens INTEGER NOT NULL DEFAULT 4096,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    """)
    con.commit()

    # 1. Sprawdzamy stan początkowy - kolumny brak
    cur.execute("PRAGMA table_info(accounts)")
    cols = [row[1] for row in cur.fetchall()]
    assert "grounding_llm_model" not in cols

    # 2. Wykonujemy logikę migracji
    if "grounding_llm_model" not in cols:
        cur.execute("ALTER TABLE accounts ADD COLUMN grounding_llm_model VARCHAR(100) DEFAULT 'gemini-2.5-flash'")
        con.commit()

    # 3. Sprawdzamy czy kolumna została dodana
    cur.execute("PRAGMA table_info(accounts)")
    cols_after = [row[1] for row in cur.fetchall()]
    assert "grounding_llm_model" in cols_after

    # 4. Ponowne uruchomienie migracji (idempotentność) nie rzuca błędu
    cur.execute("PRAGMA table_info(accounts)")
    cols_check = [row[1] for row in cur.fetchall()]
    if "grounding_llm_model" not in cols_check:
        cur.execute("ALTER TABLE accounts ADD COLUMN grounding_llm_model VARCHAR(100) DEFAULT 'gemini-2.5-flash'")
    con.close()


def test_osint_engine_search_google_grounding_model_resolution():
    """Weryfikuje wybór i oczyszczanie modelu w OSINTEngine._search_google."""
    engine = OSINTEngine()

    mock_llm_result = LLMResult(
        text='[{"tytul": "Przetarg Wagowy", "url": "https://bzp.gov.pl/1", "zrodlo": "Google", "termin": "2026-12-31"}]',
        input_tokens=100,
        output_tokens=50,
        model="gemini-2.5-pro",
        provider="Gemini",
        raw_response=MagicMock()
    )

    # 1. Konto z dedykowanym grounding_llm_model = 'gemini-2.5-pro'
    mock_account = MagicMock()
    mock_account.grounding_llm_model = "gemini-2.5-pro"
    mock_account.custom_prompt = None
    mock_account.llm_temperature = 0.2
    mock_account.llm_max_tokens = 4096
    mock_account.target_keywords = '["wagi samochodowe"]'

    with patch("src.osint_engine.generate_content_with_llm", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_result
        leads, status, resp_hash, c_chunks, q_count, in_tok, out_tok = engine._search_google(
            start_date="2026-10-01",
            today_date="2026-10-08",
            account=mock_account
        )

        assert mock_gen.called
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-pro"
        # Sprawdzamy czy tools GoogleSearch został dołączony
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) == 1

    # 2. Konto z prefixem '~' (np. ~gemini-2.0-flash)
    mock_account.grounding_llm_model = "~gemini-2.0-flash"
    with patch("src.osint_engine.generate_content_with_llm", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_result
        leads, status, resp_hash, c_chunks, q_count, in_tok, out_tok = engine._search_google(
            start_date="2026-10-01",
            today_date="2026-10-08",
            account=mock_account
        )

        assert mock_gen.called
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["model"] == "gemini-2.0-flash"
        assert call_kwargs["tools"] is not None

    # 3. Fallback do get_db_setting_sync gdy account jest None
    with patch("src.osint_engine.get_db_setting_sync", return_value="gemini-1.5-pro") as mock_setting, \
         patch("src.osint_engine.generate_content_with_llm", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_result
        leads, status, resp_hash, c_chunks, q_count, in_tok, out_tok = engine._search_google(
            start_date="2026-10-01",
            today_date="2026-10-08",
            account=None
        )

        assert mock_gen.called
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["model"] == "gemini-1.5-pro"
        assert call_kwargs["tools"] is not None


@pytest.mark.anyio
async def test_api_account_create_and_update_grounding_model(setup_auth):
    """Weryfikuje API create i update z polem grounding_llm_model."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create
        create_payload = {
            "name": "Kampania Test Grounding API",
            "target_cpvs": ["42923110-6"],
            "target_keywords": ["waga", "wagi"],
            "enabled_sources": ["Google"],
            "llm_model": "anthropic/claude-3.7-sonnet",
            "grounding_llm_model": "gemini-2.5-pro",
            "llm_temperature": 0.1,
            "llm_max_tokens": 4096,
            "is_active": True
        }
        res_create = await ac.post("/api/accounts", json=create_payload)
        assert res_create.status_code == 200, res_create.text
        data = res_create.json()
        account_id = data["id"]
        assert data["grounding_llm_model"] == "gemini-2.5-pro"
        assert data["llm_model"] == "anthropic/claude-3.7-sonnet"

        # Update
        update_payload = {
            "name": "Kampania Test Grounding API Updated",
            "target_cpvs": ["42923110-6"],
            "target_keywords": ["waga", "wagi"],
            "enabled_sources": ["Google", "BZP"],
            "llm_model": "anthropic/claude-3.7-sonnet",
            "grounding_llm_model": "gemini-2.0-flash",
            "llm_temperature": 0.2,
            "llm_max_tokens": 4096,
            "is_active": True
        }
        res_update = await ac.put(f"/api/accounts/{account_id}", json=update_payload)
        assert res_update.status_code == 200, res_update.text
        updated_data = res_update.json()
        assert updated_data["grounding_llm_model"] == "gemini-2.0-flash"

        # List
        res_list = await ac.get("/api/accounts")
        assert res_list.status_code == 200
        accounts = res_list.json()
        matched = [a for a in accounts if a["id"] == account_id]
        assert len(matched) == 1
        assert matched[0]["grounding_llm_model"] == "gemini-2.0-flash"

        # Cleanup
        await ac.delete(f"/api/accounts/{account_id}")
