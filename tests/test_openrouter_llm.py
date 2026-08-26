"""
test_openrouter_llm.py — Unit tests for OpenRouter & unified LLM integration (PLAN-054).
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from src.llm_client import (
    generate_content_with_llm,
    fetch_available_models,
    is_openrouter_model,
    LLMResult,
    OPENROUTER_API_URL,
    OPENROUTER_AUTH_URL,
    OPENROUTER_MODELS_URL
)
from main import app, get_current_user
from models import User


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


async def override_current_user():
    return User(id=1, username="admin", role="admin")


@pytest.fixture
def setup_auth():
    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_is_openrouter_model():
    assert is_openrouter_model("anthropic/claude-3.7-sonnet") is True
    assert is_openrouter_model("openai/gpt-4o") is True
    assert is_openrouter_model("deepseek/deepseek-chat") is True
    assert is_openrouter_model("openrouter/gemini-2.5-flash") is True
    assert is_openrouter_model("gemini-2.5-flash") is False
    assert is_openrouter_model("gemini-2.5-pro") is False
    assert is_openrouter_model("") is False


@pytest.mark.anyio
async def test_openrouter_chat_completion_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "gen-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"tytul": "Testowy Lead OpenRouter"}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 45
        }
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client

    with patch("src.llm_client.httpx.AsyncClient", return_value=mock_client), \
         patch("src.llm_client.get_db_setting_sync", return_value="sk-or-test-key-123"):
        result = await generate_content_with_llm(
            model="anthropic/claude-3.7-sonnet",
            prompt="Wyszukaj leady",
            system_instruction="Jesteś asystentem OSINT",
            temperature=0.2,
            max_output_tokens=1000
        )

        assert isinstance(result, LLMResult)
        assert result.provider == "OpenRouter"
        assert result.model == "anthropic/claude-3.7-sonnet"
        assert '{"tytul": "Testowy Lead OpenRouter"}' in result.text
        assert result.input_tokens == 150
        assert result.output_tokens == 45


@pytest.mark.anyio
async def test_gemini_routing():
    mock_response = MagicMock()
    mock_response.text = '{"tytul": "Testowy Lead Gemini"}'
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 100
    mock_usage.candidates_token_count = 30
    mock_response.usage_metadata = mock_usage

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client), \
         patch("src.llm_client.get_db_setting_sync", return_value="gemini-fake-key"):
        result = await generate_content_with_llm(
            model="gemini-2.5-flash",
            prompt="Test prompt",
            system_instruction="Sys prompt",
            temperature=0.1
        )

        assert isinstance(result, LLMResult)
        assert result.provider == "Gemini"
        assert result.model == "gemini-2.5-flash"
        assert result.text == '{"tytul": "Testowy Lead Gemini"}'
        assert result.input_tokens == 100
        assert result.output_tokens == 30


@pytest.mark.anyio
async def test_fetch_available_models_merging():
    import src.llm_client as llm_module
    llm_module._cached_models = None
    llm_module._cache_timestamp = 0.0

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1"},
            {"id": "anthropic/claude-3.7-sonnet", "name": "Claude 3.7 Sonnet"}
        ]
    }

    mock_httpx = AsyncMock()
    mock_httpx.get.return_value = mock_resp
    mock_httpx.__aenter__.return_value = mock_httpx

    mock_m1 = MagicMock()
    mock_m1.name = "models/gemini-2.5-flash"
    mock_m1.supported_generation_methods = ["generateContent"]
    mock_m1.display_name = "Gemini 2.5 Flash"

    mock_client = MagicMock()
    mock_client.models.list.return_value = [mock_m1]

    with patch("google.genai.Client", return_value=mock_client), \
         patch("src.llm_client.httpx.AsyncClient", return_value=mock_httpx), \
         patch("src.llm_client.get_db_setting_sync", side_effect=lambda k, d="": "key-val" if k in ("GEMINI_API_KEY", "OPENROUTER_API_KEY") else d):
        models = await fetch_available_models(force_refresh=True)

        assert len(models) >= 3
        providers = {m["provider"] for m in models}
        assert "Gemini" in providers
        assert "OpenRouter" in providers

        ids = [m["id"] for m in models]
        assert "gemini-2.5-flash" in ids
        assert "anthropic/claude-3.7-sonnet" in ids
        # Check alphabetical sorting of OpenRouter models
        or_names = [m["name"] for m in models if m["provider"] == "OpenRouter"]
        assert or_names == sorted(or_names, key=lambda x: x.lower())


@pytest.mark.anyio
async def test_fetch_available_models_without_api_key():
    import src.llm_client as llm_module
    llm_module._cached_models = None
    llm_module._cache_timestamp = 0.0

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
            {"id": "mistralai/mistral-large-2411", "name": "Mistral Large 2411"},
            {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku"}
        ]
    }

    mock_httpx = AsyncMock()
    mock_httpx.get.return_value = mock_resp
    mock_httpx.__aenter__.return_value = mock_httpx

    with patch("src.llm_client.httpx.AsyncClient", return_value=mock_httpx), \
         patch("src.llm_client.get_db_setting_sync", return_value=""):
        models = await fetch_available_models(force_refresh=True)

        # Gemini should fallback to DEFAULT_GEMINI_MODELS since no key
        gemini_ids = [m["id"] for m in models if m["provider"] == "Gemini"]
        assert "gemini-2.5-flash" in gemini_ids

        # OpenRouter should have fetched models from public endpoint without key
        or_models = [m for m in models if m["provider"] == "OpenRouter"]
        assert len(or_models) == 3
        assert [m["name"] for m in or_models] == ["Claude 3.5 Haiku", "Llama 3.3 70B", "Mistral Large 2411"]

        # Verify get called without Authorization header
        call_args = mock_httpx.get.call_args
        assert "Authorization" not in call_args.kwargs.get("headers", {})


@pytest.mark.anyio
async def test_fetch_available_models_caching():
    import src.llm_client as llm_module
    llm_module._cached_models = None
    llm_module._cache_timestamp = 0.0

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "openai/gpt-4o", "name": "GPT-4o"}
        ]
    }

    mock_httpx = AsyncMock()
    mock_httpx.get.return_value = mock_resp
    mock_httpx.__aenter__.return_value = mock_httpx

    with patch("src.llm_client.httpx.AsyncClient", return_value=mock_httpx), \
         patch("src.llm_client.get_db_setting_sync", return_value=""):
        # First call fetches and caches
        res1 = await fetch_available_models()
        assert mock_httpx.get.call_count == 1
        assert any(m["id"] == "openai/gpt-4o" for m in res1)

        # Second call should use cache (no new get call)
        res2 = await fetch_available_models()
        assert mock_httpx.get.call_count == 1
        assert res1 == res2

        # Third call with force_refresh=True should fetch again
        res3 = await fetch_available_models(force_refresh=True)
        assert mock_httpx.get.call_count == 2
        assert res3 == res1


@pytest.mark.anyio
async def test_verify_credentials_openrouter(setup_auth):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"label": "test-key"}}

    mock_httpx = AsyncMock()
    mock_httpx.get.return_value = mock_resp
    mock_httpx.__aenter__.return_value = mock_httpx

    with patch("httpx.AsyncClient", return_value=mock_httpx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/settings/verify-credentials",
                json={
                    "scraper": "OpenRouter",
                    "username": "",
                    "password": "sk-or-valid-key"
                }
            )
            assert resp.status_code == 200
            assert resp.json().get("success") is True


@pytest.mark.anyio
async def test_verify_credentials_openrouter_invalid(setup_auth):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    mock_httpx = AsyncMock()
    mock_httpx.get.return_value = mock_resp
    mock_httpx.__aenter__.return_value = mock_httpx

    with patch("httpx.AsyncClient", return_value=mock_httpx):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/settings/verify-credentials",
                json={
                    "scraper": "OpenRouter",
                    "username": "",
                    "password": "sk-or-invalid-key"
                }
            )
            assert resp.status_code == 400
            assert "Nieprawidłowy klucz" in resp.json().get("detail")
