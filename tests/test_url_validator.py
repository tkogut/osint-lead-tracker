"""
tests/test_url_validator.py — Testy jednostkowe dla URL Validator i Redirect Unpacker (Plan 064).
"""

import socket
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.url_validator import validate_and_resolve_url


@pytest.mark.asyncio
async def test_placeholder_urls_rejected():
    """Test odrzucania jawnych placeholderów i halucynacji LLM."""
    placeholders = [
        "https://ezamowienia.gov.pl/moj-przetarg/123456789/szczegoly",
        "http://bip.gmina-x.pl/zamowienia/publiczne",
        "https://platformazakupowa.pl/transakcja/987654321",
        "https://example.com/przetarg-waga",
        "https://przetargi.pl/00000000/zamowienie",
        "https://dummy-portal.pl/przetarg",
    ]

    for p_url in placeholders:
        is_valid, resolved_url, reason = await validate_and_resolve_url(p_url)
        assert is_valid is False, f"URL {p_url} powinien zostać odrzucony jako placeholder"
        assert resolved_url == p_url
        assert "Placeholder" in reason or "fake" in reason.lower()


@pytest.mark.asyncio
async def test_invalid_scheme_and_format():
    """Test odrzucania niepoprawnych schematów i pustych adresów URL."""
    invalid_urls = [
        "",
        "   ",
        "ftp://bip.gov.pl/przetarg",
        "mailto:kontakt@elewarr.pl",
        "not-a-valid-url",
        "https://",
    ]

    for inv_url in invalid_urls:
        is_valid, resolved_url, reason = await validate_and_resolve_url(inv_url)
        assert is_valid is False
        assert is_valid is False


@pytest.mark.asyncio
async def test_non_existent_dns_domain_rejected():
    """Test odrzucania domen z błędem DNS (NXDOMAIN)."""
    fake_domain = "https://invalid-non-existent-subdomain-999999999.xyz/postepowanie/1"

    is_valid, resolved_url, reason = await validate_and_resolve_url(fake_domain)
    assert is_valid is False
    assert "DNS" in reason or "domena nie istnieje" in reason


@pytest.mark.asyncio
async def test_redirect_unpacking_vertexaisearch():
    """Test rozwijania przekierowania z Google Vertex AI Search do bezpośredniej domeny docelowej."""
    fake_grounding_url = (
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/ABC123XYZ"
    )
    target_destination = "https://elewarr.pl/bip/ogloszenia/przetarg-waga-samochodowa-2026"

    # Mockujemy DNS dla vertexaisearch.cloud.google.com na True
    with patch("src.url_validator._resolve_dns", return_value=True):
        # Mockujemy httpx.AsyncClient
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.url = httpx.URL(target_destination)

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            is_valid, resolved_url, reason = await validate_and_resolve_url(fake_grounding_url)

            assert is_valid is True
            assert resolved_url == target_destination
            assert reason == "OK"


@pytest.mark.asyncio
async def test_login_walls_and_auth_required_accepted_as_valid():
    """Test traktowania bramek logowania (401, 403) jako istniejących i poprawnych hostów."""
    e2b_login_url = "https://pkpcargo.eb2b.com.pl/auth/login"

    with patch("src.url_validator._resolve_dns", return_value=True):
        for status_code in (401, 403):
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = status_code
            mock_response.url = httpx.URL(e2b_login_url)

            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                is_valid, resolved_url, reason = await validate_and_resolve_url(e2b_login_url)
                assert is_valid is True
                assert resolved_url == e2b_login_url
                assert reason == "OK"


@pytest.mark.asyncio
async def test_not_found_404_and_410_rejected():
    """Test odrzucania stron zwracających status 404 lub 410."""
    dead_url = "https://bip.warszawa.pl/nieistniejaca-strona-404"

    with patch("src.url_validator._resolve_dns", return_value=True):
        for status_code in (404, 410):
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = status_code
            mock_response.url = httpx.URL(dead_url)

            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                is_valid, resolved_url, reason = await validate_and_resolve_url(dead_url)
                assert is_valid is False
                assert resolved_url == dead_url
                assert f"HTTP {status_code} Not Found" in reason
