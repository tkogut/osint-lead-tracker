"""
logintrade.py — Wtyczka skrapera dla portalu logintrade.pl z omijaniem Cloudflare via curl_cffi.
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


class LogintradeScraper(BaseScraper):
    """
    Dedykowany skraper dla portalu logintrade.pl (zapytania ofertowe).
    """

    def __init__(self) -> None:
        super().__init__(source_name="Logintrade")
        self.base_url = "https://logintrade.pl/zapytania-ofertowe"

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            today_dt = datetime.strptime(today_date, "%Y-%m-%d").date()
            search_window_days = (today_dt - start_dt).days
        except Exception as date_err:
            logger.warning("[Logintrade] Blad parsowania start_date (%s) lub today_date (%s): %s", start_date, today_date, date_err)
            search_window_days = 7
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception:
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
            "Referer": "https://logintrade.pl/",
        }

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            for page in range(1, 11):
                url = self.base_url if page == 1 else f"{self.base_url}?page={page}"
                try:
                    logger.info("[Logintrade] Pobieranie listy zapytan ofertowych ze strony %d: %s...", page, url)
                    resp = await session.get(url, timeout=15)
                    
                    if resp.status_code != 200:
                        logger.warning("[Logintrade] Nieprawidlowy status HTTP na stronie %d: %s", page, resp.status_code)
                        continue

                    html = resp.text
                    if "Just a moment..." in html or "Cloudflare" in html and resp.status_code == 403:
                        logger.error("[Logintrade] Wykryto blokade Cloudflare / Captcha na stronie %d!", page)
                        continue

                    found_links = set(re.findall(r'href=["\']([^"\']*(?:zapytania-ofertowe|przetargi|zapytania_email)[^"\']*)["\']', html))
                    detail_urls = []
                    for link in found_links:
                        if link.endswith("/zapytania-ofertowe") or link.endswith("/zapytania-ofertowe/") or link.endswith("/przetargi") or link.endswith("/przetargi/") or link.endswith("/zapytania_email") or link.endswith("/zapytania_email/"):
                            continue
                        if link.startswith("http"):
                            if "logintrade.net" in link or "logintrade.pl" in link:
                                full_url = link
                            else:
                                continue
                        else:
                            full_url = urllib.parse.urljoin(url, link)
                        detail_urls.append(full_url)

                    if not detail_urls:
                        logger.info("[Logintrade] Strona %d nie miala nowych linkow.", page)
                        continue

                    unvisited_urls = []
                    for detail_url in detail_urls:
                        if account and hasattr(account, "id"):
                            if await is_url_visited(detail_url, account.id):
                                continue
                        unvisited_urls.append(detail_url)

                    if not unvisited_urls:
                        logger.info("[Logintrade] Wszystkie ogloszenia na stronie %d byly juz odwiedzone. Przechodze do nastepnej strony.", page)
                        continue

                    logger.info("[Logintrade] Znaleziono %d nowych linkow ogloszen na stronie %d.", len(unvisited_urls), page)

                    for detail_url in unvisited_urls:
                        await asyncio.sleep(random.uniform(0.8, 2.2))

                        try:
                            detail_resp = await session.get(detail_url, timeout=15)
                            if detail_resp.status_code != 200:
                                logger.warning("[Logintrade] Blad pobierania szczegolow %s: %s", detail_url, detail_resp.status_code)
                                continue

                            detail_html = detail_resp.text

                            pub_date_str = None
                            pub_match = re.search(r"(\d{4}-\d{2}-\d{2})", detail_html)
                            if pub_match:
                                pub_date_str = pub_match.group(1)

                            if pub_date_str:
                                try:
                                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                                    if start_dt and pub_date < start_dt:
                                        logger.info(f"[Logintrade] Napotkano ogloszenie starsze niz start_date ({start_date}). Przerywam paginacje.")
                                        return raw_items
                                except Exception as parse_pub_err:
                                    logger.warning("[Logintrade] Blad parsowania wyciagnietej daty %s: %s", pub_date_str, parse_pub_err)

                            clean_text = DOMSanitizer.clean(detail_html, max_chars=6000)

                            if len(clean_text) < 50:
                                logger.warning("[Logintrade] Odrzucono zbyt krotki tekst po sanitacji DOM: %s", detail_url)
                                if account and hasattr(account, "id"):
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            if keywords:
                                text_lower = clean_text.lower()
                                has_keyword = any(k in text_lower for k in keywords)

                                if not has_keyword:
                                    logger.debug("[Logintrade] Brak slow kluczowych w %s (SKIPPED pre-filter)", detail_url)
                                    if account and hasattr(account, "id"):
                                        await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                    continue

                            title_match = re.search(r"<h1[^>]*>(.*?)</h1>", detail_html, flags=re.DOTALL | re.IGNORECASE)
                            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else "Zapytanie ofertowe - Logintrade"

                            raw_items.append({
                                "url": detail_url,
                                "tytul": title,
                                "raw_text": clean_text,
                                "data": pub_date_str if pub_date_str else datetime.utcnow().strftime("%Y-%m-%d"),
                            })
                            logger.info("[Logintrade] Pobrano nowa tresc ogloszenia do ekstrakcji LLM: %s", title)
                            
                            if account and hasattr(account, "id"):
                                await mark_url_visited(detail_url, account.id, self.source_name, status="PROCESSED")

                        except Exception as detail_err:
                            logger.error("[Logintrade] Blad skanowania szczegolow %s: %s", detail_url, detail_err)

                except Exception as page_err:
                    logger.error("[Logintrade] Wyjatek podczas skanowania strony %d: %s", page, page_err)

        return raw_items
