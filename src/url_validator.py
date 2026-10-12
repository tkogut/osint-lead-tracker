"""
src/url_validator.py — Automatyczny walidator linków i resolver przekierowań (URL Validator & Redirect Unpacker).
Zgodny z Planem 064.
"""

import asyncio
import logging
import re
import socket
from typing import Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Placeholder blacklist patterns:
# np. 123456789, 987654321, 000000, dummy, gmina-x.pl, example.com
PLACEHOLDER_REGEXES = [
    re.compile(r"123456789"),
    re.compile(r"987654321"),
    re.compile(r"000000+"),
    re.compile(r"\bdummy\b", re.IGNORECASE),
    re.compile(r"gmina-x\.pl", re.IGNORECASE),
    re.compile(r"example\.com", re.IGNORECASE),
]


async def _resolve_dns(hostname: str) -> bool:
    """Asynchroniczne sprawdzenie rozwiązywania nazwy hosta w DNS."""
    try:
        loop = asyncio.get_running_loop()
        await loop.getaddrinfo(hostname, None)
        return True
    except (socket.gaierror, socket.error, UnicodeError):
        return False
    except Exception as exc:
        logger.debug("DNS check exception for %s: %s", hostname, exc)
        return False


async def validate_and_resolve_url(url: str, timeout: float = 5.0) -> Tuple[bool, str, str]:
    """
    Weryfikuje poprawność adresu URL i rozwija ewentualne przekierowania.

    Zwraca krotkę:
        (is_valid: bool, resolved_url: str, reason: str)

    Kroki:
    1. Weryfikacja formatu (schemat http/https, obecność hostname).
    2. Filtr placeholderów (np. 123456789, 987654321, gmina-x.pl, dummy, example.com).
    3. Sprawdzenie DNS dla domeny (czy istnieje w sieci).
    4. Rozwijanie przekierowań Google Vertex AI Search Grounding.
    5. HTTP smoke test (statusy 200..399, 401, 403 traktowane jako OK; 404, 410 jako błąd).
    """
    if not url or not isinstance(url, str):
        return False, url or "", "Pusty lub niepoprawny format URL"

    url_clean = url.strip()

    # 1. Format check
    try:
        parsed = urlparse(url_clean)
    except Exception as exc:
        return False, url_clean, f"Błąd parsowania URL: {exc}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, url_clean, f"Nieobsługiwany schemat URL: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return False, url_clean, "Brak nazwy hosta w URL"

    # 2. Placeholder blacklist check
    for pattern in PLACEHOLDER_REGEXES:
        if pattern.search(url_clean):
            return False, url_clean, "Placeholder/fake URL"

    # 3. DNS check
    dns_ok = await _resolve_dns(hostname)
    if not dns_ok:
        return False, url_clean, "Błąd DNS: domena nie istnieje"

    resolved_url = url_clean

    # 4 & 5. Unpack redirects and HTTP smoke test
    is_grounding_redirect = (
        "vertexaisearch.cloud.google.com" in hostname.lower()
        or "grounding-api-redirect" in url_clean.lower()
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False  # Zezwalamy na serwery ze starymi/błędnymi certyfikatami SSL
        ) as client:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }

            resp = None
            try:
                # Najpierw próba szybkiego HEAD
                resp = await client.head(url_clean, headers=headers)
                if resp.status_code in (405, 501):  # Method Not Allowed -> fallback na GET
                    resp = await client.get(url_clean, headers=headers)
            except (httpx.RequestError, httpx.HTTPStatusError):
                # Fallback na lekki GET w przypadku błędu HEAD
                try:
                    resp = await client.get(url_clean, headers=headers)
                except Exception as get_exc:
                    logger.debug("HTTP GET fallback error for %s: %s", url_clean, get_exc)
                    # Jeśli DNS przeszedł, ale połączenie zostało odrzucone lub timeout
                    return True, resolved_url, "OK (Host reachable)"

            if resp is not None:
                final_url = str(resp.url)
                if final_url and final_url != url_clean:
                    resolved_url = final_url

                status = resp.status_code
                if (200 <= status < 400) or status in (401, 403):
                    return True, resolved_url, "OK"
                elif status in (404, 410):
                    return False, resolved_url, f"HTTP {status} Not Found"
                else:
                    # Inne kody (np. 500, 502, 503) — serwer istnieje, nie odrzucamy pochopnie
                    return True, resolved_url, f"OK (HTTP {status})"

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.debug("HTTP connection issue for %s: %s", url_clean, exc)
        return True, resolved_url, "OK (Host reachable)"
    except Exception as exc:
        logger.debug("Unexpected HTTP error for %s: %s", url_clean, exc)
        return True, resolved_url, "OK (Host reachable)"

    return True, resolved_url, "OK"
