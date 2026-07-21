"""
automatyka.py — Wtyczka skrapera dla portalu automatyka.pl z omijaniem Cloudflare via curl_cffi.
"""

import asyncio
import logging
import random
import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any

from curl_cffi.requests import AsyncSession
from scrapers.base import BaseScraper, DOMSanitizer
from database import is_url_visited, mark_url_visited

logger = logging.getLogger(__name__)


class AutomatykaScraper(BaseScraper):
    """
    Dedykowany skraper dla portalu automatyka.pl (zapytania ofertowe).
    """

    def __init__(self) -> None:
        super().__init__(source_name="Automatyka")
        self.base_url = "https://www.automatyka.pl/zapytania-ofertowe"

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []

        keywords = ["waga", "wagi", "wag", "ważeń", "ważen", "najazd"]
        if hasattr(account, "target_keywords") and account.target_keywords:
            try:
                import json
                parsed_kws = json.loads(account.target_keywords)
                if parsed_kws:
                    keywords = [k.lower().strip() for k in parsed_kws]
            except Exception:
                pass

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
            "Referer": "https://www.automatyka.pl/",
        }

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            try:
                logger.info("[Automatyka] Pobieranie listy zapytań ofertowych z %s...", self.base_url)
                resp = await session.get(self.base_url, timeout=15)
                
                if resp.status_code != 200:
                    logger.warning("[Automatyka] Nieprawidłowy status HTTP: %s", resp.status_code)
                    return []

                html = resp.text
                if "Just a moment..." in html or "Cloudflare" in html and resp.status_code == 403:
                    logger.error("[Automatyka] Wykryto blokadę Cloudflare / Captcha!")
                    return []

                # Ekstrakcja unikalnych linków do ogłoszeń z listy
                found_links = set(re.findall(r'href=["\'](/zapytania-ofertowe/[^"\']+)["\']', html))
                detail_urls = []
                for link in found_links:
                    if link == "/zapytania-ofertowe" or link.endswith("/zapytania-ofertowe/"):
                        continue
                    full_url = urllib.parse.urljoin(self.base_url, link)
                    detail_urls.append(full_url)

                logger.info("[Automatyka] Znaleziono %d linków ogłoszeń na liście.", len(detail_urls))

                # Pętla po ogłoszeniach z uwzględnieniem Tier 0 deduplikacji (visited_urls)
                for detail_url in detail_urls[:20]:  # Limit 20 na skan
                    if account and hasattr(account, "id"):
                        if await is_url_visited(detail_url, account.id):
                            logger.debug("[Automatyka] Pomięto już odwiedzony URL (Tier 0): %s", detail_url)
                            continue

                    # Losowy jitter opóźnienia rate limiting
                    await asyncio.sleep(random.uniform(0.8, 2.2))

                    try:
                        detail_resp = await session.get(detail_url, timeout=15)
                        if detail_resp.status_code != 200:
                            logger.warning("[Automatyka] Błąd pobierania szczegółów %s: %s", detail_url, detail_resp.status_code)
                            continue

                        detail_html = detail_resp.text
                        clean_text = DOMSanitizer.clean(detail_html, max_chars=6000)

                        if len(clean_text) < 50:
                            logger.warning("[Automatyka] Odrzucono zbyt krótki tekst po sanitacji DOM: %s", detail_url)
                            if account and hasattr(account, "id"):
                                await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                            continue

                        # Sprawdzenie słów kluczowych pre-filter
                        text_lower = clean_text.lower()
                        has_keyword = any(k in text_lower for k in keywords)

                        if not has_keyword:
                            logger.debug("[Automatyka] Brak słów kluczowych w %s (SKIPPED pre-filter)", detail_url)
                            if account and hasattr(account, "id"):
                                await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                            continue

                        # Próbujemy wyciągnąć prosty tytuł
                        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", detail_html, flags=re.DOTALL | re.IGNORECASE)
                        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else "Zapytanie ofertowe - Automatyka.pl"

                        raw_items.append({
                            "url": detail_url,
                            "tytul": title,
                            "raw_text": clean_text,
                            "data": datetime.utcnow().strftime("%Y-%m-%d"),
                        })
                        logger.info("[Automatyka] Pobrano nową treść ogłoszenia do ekstrakcji LLM: %s", title)

                    except Exception as detail_err:
                        logger.error("[Automatyka] Błąd skanowania szczegółów %s: %s", detail_url, detail_err)

            except Exception as e:
                logger.error("[Automatyka] Wyjątek podczas skanowania portalu: %s", e)

        return raw_items
