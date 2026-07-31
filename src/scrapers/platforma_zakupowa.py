"""
platforma_zakupowa.py — Wtyczka skrapera dla portalu platformazakupowa.pl (Open Nexus) w trybie publicznym.
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
from src.utils import match_polish_keywords

logger = logging.getLogger(__name__)


class PlatformaZakupowaScraper(BaseScraper):
    """
    Dedykowany skraper dla portalu platformazakupowa.pl (Open Nexus) do pobierania publicznych postępowań.
    """

    def __init__(self) -> None:
        super().__init__(source_name="PlatformaZakupowa")
        self.base_url = "https://platformazakupowa.pl/all"

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except Exception as date_err:
            logger.warning("[PlatformaZakupowa] Blad parsowania start_date (%s): %s", start_date, date_err)
            start_dt = None

        keywords = []
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
            "Referer": "https://platformazakupowa.pl/",
        }

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            try:
                logger.info("[PlatformaZakupowa] Inicjalizacja sesji cookie na %s", self.base_url)
                await session.get(self.base_url, timeout=15)
            except Exception as init_err:
                logger.warning("[PlatformaZakupowa] Blad inicjalizacji sesji cookie: %s", init_err)

            for page in range(1, 11):
                url = f"https://platformazakupowa.pl/all?page={page}&limit=30"
                try:
                    logger.info("[PlatformaZakupowa] Pobieranie listy postepowan ze strony %d: %s...", page, url)
                    resp = await session.get(url, timeout=15)

                    if resp.status_code != 200:
                        logger.warning("[PlatformaZakupowa] Nieprawidlowy status HTTP na stronie %d: %s", page, resp.status_code)
                        continue

                    html = resp.text
                    if "Just a moment..." in html or ("Cloudflare" in html and resp.status_code == 403):
                        logger.error("[PlatformaZakupowa] Wykryto blokade Cloudflare / Captcha na stronie %d!", page)
                        continue

                    raw_links = set(re.findall(r'href=["\']([^"\']*/transakcja/[^"\']*)["\']', html))
                    detail_urls = []
                    for link in raw_links:
                        if link.startswith("http"):
                            if "platformazakupowa.pl" in link:
                                full_url = link
                            else:
                                continue
                        else:
                            full_url = urllib.parse.urljoin("https://platformazakupowa.pl", link)
                        if full_url not in detail_urls:
                            detail_urls.append(full_url)

                    if not detail_urls:
                        logger.info("[PlatformaZakupowa] Strona %d nie miala nowych linkow.", page)
                        continue

                    unvisited_urls = []
                    for detail_url in detail_urls:
                        if account and hasattr(account, "id") and account.id:
                            if await is_url_visited(detail_url, account.id):
                                continue
                        unvisited_urls.append(detail_url)

                    if not unvisited_urls:
                        logger.info("[PlatformaZakupowa] Wszystkie ogloszenia na stronie %d byly juz odwiedzone. Przechodze do nastepnej strony.", page)
                        continue

                    logger.info("[PlatformaZakupowa] Znaleziono %d nowych linkow ogloszen na stronie %d.", len(unvisited_urls), page)

                    for detail_url in unvisited_urls:
                        await asyncio.sleep(random.uniform(0.8, 2.0))

                        try:
                            detail_resp = await session.get(detail_url, timeout=15)
                            if detail_resp.status_code != 200:
                                logger.warning("[PlatformaZakupowa] Blad pobierania szczegolow %s: %s", detail_url, detail_resp.status_code)
                                continue

                            detail_html = detail_resp.text

                            pub_date_str = None
                            pub_match = re.search(r"(\d{4}-\d{2}-\d{2})", detail_html)
                            if pub_match:
                                pub_date_str = pub_match.group(1)

                            if pub_date_str and start_dt:
                                try:
                                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                                    if pub_date < start_dt:
                                        logger.info("[PlatformaZakupowa] Napotkano ogloszenie starsze niz start_date (%s). Przerywam paginacje.", start_date)
                                        return raw_items
                                except Exception as parse_pub_err:
                                    logger.warning("[PlatformaZakupowa] Blad parsowania daty %s: %s", pub_date_str, parse_pub_err)

                            clean_text = DOMSanitizer.clean(detail_html, max_chars=6000)

                            if len(clean_text) < 50:
                                logger.warning("[PlatformaZakupowa] Odrzucono zbyt krotki tekst po sanitacji DOM: %s", detail_url)
                                if account and hasattr(account, "id") and account.id:
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            if keywords:
                                text_lower = clean_text.lower()
                                has_keyword = match_polish_keywords(text_lower, keywords)

                                if not has_keyword:
                                    logger.debug("[PlatformaZakupowa] Brak slow kluczowych w %s (SKIPPED pre-filter)", detail_url)
                                    if account and hasattr(account, "id") and account.id:
                                        await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                    continue

                            title_match = re.search(r"<h1[^>]*>(.*?)</h1>", detail_html, flags=re.DOTALL | re.IGNORECASE)
                            if not title_match:
                                title_match = re.search(r"<title[^>]*>(.*?)</title>", detail_html, flags=re.DOTALL | re.IGNORECASE)
                            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else "Postepowanie - PlatformaZakupowa.pl"

                            raw_items.append({
                                "url": detail_url,
                                "tytul": title,
                                "raw_text": clean_text,
                                "data": pub_date_str if pub_date_str else datetime.utcnow().strftime("%Y-%m-%d"),
                            })
                            logger.info("[PlatformaZakupowa] Pobrano nowa tresc postepowania do ekstrakcji LLM: %s", title)

                            if account and hasattr(account, "id") and account.id:
                                await mark_url_visited(detail_url, account.id, self.source_name, status="PROCESSED")

                        except Exception as detail_err:
                            logger.error("[PlatformaZakupowa] Blad skanowania szczegolow %s: %s", detail_url, detail_err)

                except Exception as page_err:
                    logger.error("[PlatformaZakupowa] Wyjatek podczas skanowania strony %d: %s", page, page_err)

        return raw_items
