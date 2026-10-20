"""
src/url_validator.py — Automatyczny walidator linków i resolver przekierowań (URL Validator & Redirect Unpacker).
Zgodny z Planem 064.
"""

import asyncio
import logging
import re
import socket
import json
from typing import Tuple, Optional, Any
from urllib.parse import urlparse

import httpx

from llm_client import generate_content_with_llm

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
    # Plan 069: Sequential patterns
    re.compile(r"\b12345\b"),
    re.compile(r"/12345(?:\b|/|\?)"),
    re.compile(r"12345$"),
    re.compile(r"\b54321\b"),
    # Plan 069: Fake subdomains of platformazakupowa/ezamowienia/bazakonkurencyjnosci
    re.compile(r"platformazakupowa\.[a-z0-9\-]+\.pl", re.IGNORECASE),
    re.compile(r"ezamowienia\.(?!gov\.pl)[a-z0-9\-]+\.pl", re.IGNORECASE),
    re.compile(r"bazakonkurencyjnosci\.[a-z0-9\-]+\.pl", re.IGNORECASE),
    # Plan 069: Fake placeholder paths
    re.compile(r"/zapytani[ea]/1234", re.IGNORECASE),
    re.compile(r"/przetargi?/1234", re.IGNORECASE),
]

# Znane prefiksy IP domen zaparkowanych / dummy (Plan 069)
PARKED_IP_PREFIXES = (
    "104.247.81.",
    "34.102.136.",
    "199.59.243.",
    "0.0.0.0",
    "127.",
)

# Zaufane domeny i portale publiczne / przetargowe (Plan 069)
TRUSTED_DOMAINS = (
    "platformazakupowa.pl",
    "logintrade.net",
    "biznes-polska.pl",
    "automatyka.pl",
    "bazakonkurencyjnosci.funduszeeuropejskie.gov.pl",
)


def _is_trusted_portal(hostname: str) -> bool:
    """Sprawdza, czy hostname należy do zaufanych portali publicznych lub rządowych."""
    if not hostname:
        return False
    h = hostname.lower()
    if h.endswith(".gov.pl") or h == "gov.pl":
        return True
    for td in TRUSTED_DOMAINS:
        if h == td or h.endswith("." + td):
            return True
    return False


def _handle_connection_failure(hostname: str, url: str, exc: Exception) -> Tuple[bool, str, str]:
    """
    Obsługa błędów połączenia HTTP/SSL.
    Dla zaufanych portali (gov.pl, platformazakupowa itp.) przy przejściowych timeoutach zachowujemy lead.
    Dla niezweryfikowanych/dowolnych domen link jest odrzucany.
    """
    if _is_trusted_portal(hostname):
        logger.info("Przejściowy problem z połączeniem dla zaufanego portalu %s: %s. Zachowywanie leada.", hostname, exc)
        return True, url, "OK (Host reachable)"
    err_msg = f"Nieosiągalny host / Błąd połączenia: {type(exc).__name__}"
    logger.warning("Odrzucono niezweryfikowany/nieosiągalny URL %s: %s", url, err_msg)
    return False, url, err_msg


async def _resolve_dns(hostname: str) -> bool:
    """Asynchroniczne sprawdzenie rozwiązywania nazwy hosta w DNS oraz filtr zaparkowanych IP."""
    try:
        loop = asyncio.get_running_loop()
        addr_info = await loop.getaddrinfo(hostname, None)
        if not addr_info:
            return False
        for item in addr_info:
            sockaddr = item[4]
            if sockaddr and isinstance(sockaddr, tuple) and len(sockaddr) > 0:
                ip_str = str(sockaddr[0])
                if any(ip_str.startswith(prefix) for prefix in PARKED_IP_PREFIXES):
                    logger.warning("DNS resolved to parked/dummy IP %s for %s", ip_str, hostname)
                    return False
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
        return False, url_clean, "Błąd DNS: domena nie istnieje lub jest zaparkowana"

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
                    return _handle_connection_failure(hostname, resolved_url, get_exc)

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

    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
        logger.debug("HTTP connection issue for %s: %s", url_clean, exc)
        return _handle_connection_failure(hostname, resolved_url, exc)
    except Exception as exc:
        logger.debug("Unexpected HTTP error for %s: %s", url_clean, exc)
        return _handle_connection_failure(hostname, resolved_url, exc)

    return True, resolved_url, "OK"


async def attempt_url_recovery(
    lead: dict,
    account: Optional[Any] = None,
    timeout: float = 12.0
) -> Tuple[bool, str, str]:
    """
    Podejmuje próbę ponownego celowanego wyszukania poprawnego URL w Google (Search Recovery).

    Zwraca krotkę:
        (is_valid: bool, recovered_or_orig_url: str, reason: str)
    """
    orig_url = (lead.get("url") or "").strip()
    investor = (
        lead.get("inwestor")
        or lead.get("nazwa_inwestora")
        or ""
    ).strip()
    title = (
        lead.get("tytul")
        or lead.get("tytul_generowany")
        or lead.get("nazwa_inwestycji")
        or ""
    ).strip()
    scope = (
        lead.get("zakres")
        or lead.get("opis_szczegolowy")
        or ""
    ).strip()

    search_parts = [p for p in [investor, title, scope[:80], "przetarg zapytanie ofertowe"] if p]
    query = " ".join(search_parts).strip()
    if not query:
        return False, orig_url, "Brak danych leada do ponownego wyszukania"

    prompt = (
        f"Odszukaj oficjalny, bezpośredni i publicznie dostępny adres URL ogłoszenia przetargowego lub zapytania ofertowego dla:\n"
        f"Inwestor: {investor}\n"
        f"Tytuł: {title}\n"
        f"Zakres: {scope[:200]}\n\n"
        f"Zwróć WYŁĄCZNIE poprawny JSON w formacie: {{\"url\": \"<bezpośredni_url>\"}} lub {{\"url\": null}} jeśli nie znaleziono.\n"
        f"Nie dodawaj żadnego komentarza ani tekstu poza blokiem JSON."
    )

    try:
        from google.genai import types

        search_tool = types.Tool(google_search=types.GoogleSearch())

        model = "gemini-2.5-flash"
        if account and hasattr(account, "grounding_llm_model") and account.grounding_llm_model:
            model = account.grounding_llm_model

        res_obj = await asyncio.wait_for(
            generate_content_with_llm(
                model=model,
                prompt=prompt,
                temperature=0.1,
                tools=[search_tool],
                timeout=timeout
            ),
            timeout=timeout
        )

        raw_text = (res_obj.text or "").strip()
        # Wyciągamy blok json
        json_match = re.search(r'\{[^{}]*"url"\s*:\s*(?:null|"[^"]*")\s*\}', raw_text, re.DOTALL)
        candidate_url = None
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                candidate_url = data.get("url")
            except Exception as j_exc:
                logger.debug("Błąd dekodowania JSON z odpowiedzi LLM: %s", j_exc)
        else:
            # Fallback regex bezpośrednio na URL w tekście jeśli model nie zwrócił czystego jsona
            url_match = re.search(r'https?://[^\s"\'<>]+', raw_text)
            if url_match:
                candidate_url = url_match.group(0)

        if candidate_url and isinstance(candidate_url, str):
            candidate_url = candidate_url.strip()
            # Przepuszczamy kandydata przez walidator
            is_valid, resolved_url, reason = await validate_and_resolve_url(candidate_url)
            if is_valid:
                logger.info(
                    "[Search Recovery] Sukces! Odzyskano poprawny URL: %s dla leada '%s'",
                    resolved_url, title[:50]
                )
                return True, resolved_url, "Odzyskano przez ponowne wyszukiwanie"
            else:
                logger.warning(
                    "[Search Recovery] Kandydat URL (%s) odrzucony: %s",
                    candidate_url, reason
                )
                return False, orig_url, f"Kandydat z ponownego wyszukania niepoprawny ({reason})"

        logger.info("[Search Recovery] Nie odnaleziono poprawnego URL dla: %s", query[:60])
        return False, orig_url, "Nie znaleziono linku w ponownym wyszukiwaniu"

    except Exception as exc:
        logger.warning("[Search Recovery] Błąd podczas próby odzyskania URL: %s", exc)
        return False, orig_url, f"Błąd ponownego wyszukiwania: {exc}"
