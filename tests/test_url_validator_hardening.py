"""
tests/test_url_validator_hardening.py — Testy uszczelnienia walidatora linków (URL Validator Hardening)
i ochrony przed halucynacjami AI oraz endpointu DELETE /api/leads/{id} (Plan 069).
"""

import asyncio
import os
import socket
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from httpx import AsyncClient, ASGITransport

from src.url_validator import (
    validate_and_resolve_url,
    _resolve_dns,
    _is_trusted_portal,
    PARKED_IP_PREFIXES,
)
from src.database import init_db, AsyncSessionLocal
from src.models import Lead, User
from src.main import app, get_current_user


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    os.makedirs("./data", exist_ok=True)
    asyncio.run(init_db())


@pytest.mark.asyncio
async def test_fake_smakpol_placeholder_url_rejected():
    """
    Test odrzucenia konkretnego adresu URL https://platformazakupowa.smakpol.pl/zapytanie/12345
    jako fałszywego leada (placeholder, zmyślona subdomena, sztuczny identyfikator).
    """
    fake_url = "https://platformazakupowa.smakpol.pl/zapytanie/12345"
    is_valid, resolved_url, reason = await validate_and_resolve_url(fake_url)

    assert is_valid is False
    assert resolved_url == fake_url
    assert "Placeholder" in reason or "fake" in reason.lower()


@pytest.mark.asyncio
async def test_sequential_patterns_and_fake_subdomains_rejected():
    """Test odrzucania sekwencji 12345, 54321 oraz fikcyjnych subdomen platform zakupowych."""
    rejected_urls = [
        "https://platformazakupowa.xyz.pl/zamowienie/test",
        "https://platformazakupowa.firma-abc.pl/zapytanie",
        "https://ezamowienia.firma.pl/przetarg",
        "https://ezamowienia.portal-testowy.pl/ogloszenie",
        "https://bazakonkurencyjnosci.firma.pl/postepowanie",
        "https://bazakonkurencyjnosci.xyz.pl/zapytania/1234",
        "https://bip.jakas-domena.pl/przetarg/12345",
        "https://bip.jakas-domena.pl/przetargi/12345?param=1",
        "https://ogloszenia.pl/postepowania/54321",
        "https://portal.pl/przetargi/1234",
        "https://portal.pl/zapytanie/1234",
        "https://portal.pl/zapytania/1234",
    ]

    for url in rejected_urls:
        is_valid, resolved_url, reason = await validate_and_resolve_url(url)
        assert is_valid is False, f"URL {url} powinien zostać odrzucony!"
        assert "Placeholder" in reason or "fake" in reason.lower()


@pytest.mark.asyncio
async def test_parked_domain_ip_rejection():
    """Test odrzucania domen rozwiązujących się do znanych adresów IP parkingów/dummy."""
    for parked_prefix in PARKED_IP_PREFIXES:
        test_ip = parked_prefix + "99" if not parked_prefix.endswith("0") else "0.0.0.0"
        mock_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (test_ip, 80))
        ]

        with patch("asyncio.get_running_loop") as mock_loop_fn:
            mock_loop = MagicMock()
            mock_loop.getaddrinfo = AsyncMock(return_value=mock_addrinfo)
            mock_loop_fn.return_value = mock_loop

            dns_result = await _resolve_dns("parked-sample-domain.com")
            assert dns_result is False, f"IP {test_ip} powinno zostać uznane za zaparkowane!"

    # Test specyficznego IP 104.247.81.99 w całym pipeline walidacji
    parked_url = "https://parked-test-domain-xyz.pl/przetarg"
    with patch("src.url_validator._resolve_dns", return_value=False):
        is_valid, resolved_url, reason = await validate_and_resolve_url(parked_url)
        assert is_valid is False
        assert "DNS" in reason or "zaparkowana" in reason


@pytest.mark.asyncio
async def test_legitimate_urls_accepted():
    """Test akceptacji poprawnych, autentycznych adresów URL platform rządowych i publicznych."""
    valid_urls = [
        "https://ezamowienia.gov.pl/mo-board/api/v1/notice",
        "https://platformazakupowa.pl/transakcja/889977",
        "https://platformazakupowa.pl/",
        "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/98712",
        "https://logintrade.net/zapytanie/999",
        "https://biznes-polska.pl/inwestycje/waga-przemyslowa",
    ]

    with patch("src.url_validator._resolve_dns", return_value=True):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        for url in valid_urls:
            mock_response.url = httpx.URL(url)
            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client

                is_valid, resolved_url, reason = await validate_and_resolve_url(url)
                assert is_valid is True, f"Legitimate URL {url} nie powinien być odrzucony (powód: {reason})"
                assert resolved_url == url
                assert reason == "OK"


@pytest.mark.asyncio
async def test_connection_failure_trusted_vs_untrusted():
    """
    Test różnicowania błędów połączenia:
    - Zaufany portal rządowy z timeoutem HTTP -> dopuszczony jako 'OK (Host reachable)'.
    - Niezweryfikowany/nieznany host z błędem SSL/ConnectError -> odrzucony jako nieosiągalny.
    """
    trusted_gov_url = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"
    untrusted_url = "https://unverified-private-company-site.pl/zapytanie"

    with patch("src.url_validator._resolve_dns", return_value=True):
        # 1. Trusted portal z błędem połączenia
        mock_client_trusted = AsyncMock()
        mock_client_trusted.head.side_effect = httpx.ConnectTimeout("Connection timed out")
        mock_client_trusted.get.side_effect = httpx.ConnectTimeout("Connection timed out")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client_trusted

            is_valid, resolved_url, reason = await validate_and_resolve_url(trusted_gov_url)
            assert is_valid is True
            assert reason == "OK (Host reachable)"

        # 2. Untrusted portal z błędem połączenia
        mock_client_untrusted = AsyncMock()
        mock_client_untrusted.head.side_effect = httpx.ConnectError("Connection refused")
        mock_client_untrusted.get.side_effect = httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client_untrusted

            is_valid, resolved_url, reason = await validate_and_resolve_url(untrusted_url)
            assert is_valid is False
            assert "Nieosiągalny host" in reason or "ConnectError" in reason


@pytest.mark.anyio
async def test_delete_lead_endpoint():
    """Test endpointu DELETE /api/leads/{id} z autoryzacją i walidacją 404."""
    # 1. Utworzenie leada testowego w bazie
    test_url = "https://platformazakupowa.pl/transakcja/test-delete-plan-069"
    test_lead_id = None
    async with AsyncSessionLocal() as session:
        lead = Lead(
            url=test_url,
            tytul="Lead testowy do usunięcia Plan 069",
            typ="Przetarg",
            inwestor="Gmina Testowa",
            zakres="Dostawa wagi",
            priorytet="wysoki",
            data_pub="2026-10-20",
            status="new",
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        test_lead_id = lead.id

    assert test_lead_id is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 2. Próba usunięcia bez autoryzacji -> 401
        res_unauth = await ac.delete(f"/api/leads/{test_lead_id}")
        assert res_unauth.status_code == 401

        # 3. Usunięcie z poprawnym tokenem API -> 200
        headers = {"X-API-Token": "test"}
        res_delete = await ac.delete(f"/api/leads/{test_lead_id}", headers=headers)
        assert res_delete.status_code == 200
        data = res_delete.json()
        assert data["success"] is True
        assert data["id"] == test_lead_id

        # 4. Sprawdzenie, że rekord zniknął z bazy
        async with AsyncSessionLocal() as session:
            db_lead = await session.get(Lead, test_lead_id)
            assert db_lead is None

        # 5. Ponowna próba usunięcia (nie istnieje) -> 404
        res_not_found = await ac.delete(f"/api/leads/{test_lead_id}", headers=headers)
        assert res_not_found.status_code == 404
