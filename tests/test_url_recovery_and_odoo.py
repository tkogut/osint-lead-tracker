"""
tests/test_url_recovery_and_odoo.py — Testy jednostkowe dla procedury URL Search Recovery oraz banera ostrzegawczego Odoo (Plan 065).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.url_validator import attempt_url_recovery
from src.odoo_integration import OdooClient
from src.llm_client import LLMResult


@pytest.mark.asyncio
async def test_attempt_url_recovery_success():
    """Test udanego odzyskania URL przez Google Search w LLM."""
    lead = {
        "tytul": "Budowa wagi samochodowej 60t",
        "inwestor": "Elewarr Sp. z o.o.",
        "zakres": "Dostawa i montaż wagi pomostowej",
        "url": "https://invalid-non-existent-broken-domain-999.pl/404"
    }

    mock_recovered_url = "https://elewarr.pl/bip/zamowienia/waga-60t"

    mock_llm_result = LLMResult(
        text=f'{{"url": "{mock_recovered_url}"}}',
        input_tokens=100,
        output_tokens=25,
        model="gemini-2.5-flash",
        provider="Gemini"
    )

    with patch("src.url_validator.generate_content_with_llm", new=AsyncMock(return_value=mock_llm_result)):
        with patch("src.url_validator.validate_and_resolve_url", new=AsyncMock(return_value=(True, mock_recovered_url, "OK"))):
            is_valid, resolved_url, reason = await attempt_url_recovery(lead)

            assert is_valid is True
            assert resolved_url == mock_recovered_url
            assert "Odzyskano przez ponowne wyszukiwanie" in reason


@pytest.mark.asyncio
async def test_attempt_url_recovery_failure_returns_original():
    """Test nieudanego odzyskania URL — model zwraca null lub link nadal niepoprawny."""
    lead = {
        "tytul": "Dostawa wagi samochodowej",
        "inwestor": "Tajemnicza Firma XYZ",
        "zakres": "Waga",
        "url": "https://example.com/fake-url"
    }

    mock_llm_result = LLMResult(
        text='{"url": null}',
        input_tokens=100,
        output_tokens=10,
        model="gemini-2.5-flash",
        provider="Gemini"
    )

    with patch("src.url_validator.generate_content_with_llm", new=AsyncMock(return_value=mock_llm_result)):
        is_valid, resolved_url, reason = await attempt_url_recovery(lead)

        assert is_valid is False
        assert resolved_url == "https://example.com/fake-url"
        assert "Nie znaleziono linku" in reason


@pytest.mark.asyncio
async def test_attempt_url_recovery_candidate_invalid():
    """Test sytuacji, gdy LLM proponuje kandydata, ale walidator odrzuca go (np. 404 lub placeholder)."""
    lead = {
        "tytul": "Montaż wagi",
        "inwestor": "Cukrownia Glinojeck",
        "url": "https://cukrownia.pl/przetarg-stary"
    }

    mock_candidate_url = "https://cukrownia.pl/przetarg-404"
    mock_llm_result = LLMResult(
        text=f'{{"url": "{mock_candidate_url}"}}',
        input_tokens=100,
        output_tokens=25,
        model="gemini-2.5-flash",
        provider="Gemini"
    )

    with patch("src.url_validator.generate_content_with_llm", new=AsyncMock(return_value=mock_llm_result)):
        with patch("src.url_validator.validate_and_resolve_url", new=AsyncMock(return_value=(False, mock_candidate_url, "HTTP 404 Not Found"))):
            is_valid, resolved_url, reason = await attempt_url_recovery(lead)

            assert is_valid is False
            assert resolved_url == "https://cukrownia.pl/przetarg-stary"
            assert "HTTP 404 Not Found" in reason


def test_odoo_warning_banner_and_title_prefix():
    """Test generowania prefiksu w tytule leada oraz banera ostrzegawczego HTML w opisie w Odoo."""
    client = OdooClient()

    lead_valid = {
        "tytul": "Przetarg na wagę samochodową",
        "inwestor": "Kopalnia Soli Kłodawa",
        "url": "https://sol-klodawa.com.pl/bip/przetarg-1",
        "typ": "Przetarg publiczny",
        "zakres": "Waga 60t",
        "uzasadnienie": "Wysoki potencjał",
        "priorytet": "wysoki"
    }

    # Mock XML-RPC methods
    created_vals = []

    def mock_execute_kw(db, uid, key, model, method, args, kwargs=None):
        if method == "search":
            return []
        if method == "create":
            created_vals.append(args[0])
            return 12345
        return None

    mock_models = MagicMock()
    mock_models.execute_kw.side_effect = mock_execute_kw

    with patch.object(client, "_authenticate", return_value=1), \
         patch.object(client, "_models_proxy", return_value=mock_models):

        # 1. Test dla poprawnego leada (url_status="valid")
        lead_id = client.create_lead(lead_valid, url_status="valid")
        assert lead_id == 12345
        assert len(created_vals) == 1
        vals_valid = created_vals[0]
        assert vals_valid["name"] == "Przetarg na wagę samochodową"
        assert "⚠️ UWAGA: Link źródłowy wymaga weryfikacji ręcznej!" not in vals_valid["description"]
        assert "⚠️ Link może być nieaktywny" not in vals_valid["description"]

        # 2. Test dla leada z niepoprawnym URL (url_status="invalid")
        created_vals.clear()
        lead_invalid = dict(lead_valid)
        lead_invalid["url"] = "https://invalid-broken-domain.pl/error"
        lead_invalid["url_status"] = "invalid"
        lead_invalid["url_error"] = "Błąd DNS: domena nie istnieje"

        lead_id_inv = client.create_lead(
            lead_invalid,
            url_status="invalid",
            url_error="Błąd DNS: domena nie istnieje"
        )
        assert lead_id_inv == 12345
        assert len(created_vals) == 1
        vals_inv = created_vals[0]

        # Weryfikacja prefiksu w nazwie
        assert vals_inv["name"] == "[⚠️ WERYFIKACJA LINKU] Przetarg na wagę samochodową"

        # Weryfikacja banera ostrzegawczego HTML w opisie
        desc = vals_inv["description"]
        assert "⚠️ UWAGA: Link źródłowy wymaga weryfikacji ręcznej!" in desc
        assert "Automatyczny weryfikator linków wykrył problem z adresem URL:" in desc
        assert "Błąd DNS: domena nie istnieje" in desc
        assert "https://invalid-broken-domain.pl/error" in desc
        assert "Kopalnia Soli Kłodawa" in desc
        assert "(⚠️ Link może być nieaktywny — wymagana weryfikacja ręczna)" in desc
