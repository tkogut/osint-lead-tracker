"""
biznes_polska.py — Wtyczka skrapera dla portalu biznes-polska.pl z dwufazowym pobieraniem.
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
from database import is_url_visited, mark_url_visited, get_db_setting_sync
from scrapers.playwright_fetcher import fetch_multiple_with_playwright
from src.utils import match_polish_keywords

logger = logging.getLogger("osint.scraper.biznes_polska")


class BiznesPolskaScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(source_name="BiznesPolska")
        self.base_url = "https://www.biznes-polska.pl/przetargi/"

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []

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
            "Referer": "https://www.biznes-polska.pl/",
        }

        user = get_db_setting_sync("SCRAPER_BIZNESPOLSKA_USER", "")
        scraper_password = get_db_setting_sync("SCRAPER_BIZNESPOLSKA_PASS", "")

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            for page in range(1, 11):
                url = self.base_url if page == 1 else f"{self.base_url}?s={page}"
                try:
                    logger.info("[BiznesPolska] Pobieranie listy ze strony %d: %s...", page, url)
                    resp = await session.get(url, timeout=15)
                    if resp.status_code != 200:
                        logger.warning("[BiznesPolska] Nieprawidłowy status HTTP na stronie %d: %s", page, resp.status_code)
                        continue

                    html = resp.text
                    if "Just a moment..." in html or "Cloudflare" in html and resp.status_code == 403:
                        logger.error("[BiznesPolska] Wykryto blokadę Cloudflare / Captcha na stronie %d!", page)
                        continue

                    # Wyciąganie unikalnych linków do szczegółów ogłoszeń
                    found_links = set(re.findall(r'href=["\'](/przetargi/[^,]+,\d+/)["\']', html))
                    detail_urls = []
                    for link in found_links:
                        full_url = urllib.parse.urljoin(self.base_url, link)
                        detail_urls.append(full_url)

                    if not detail_urls:
                        logger.info("[BiznesPolska] Strona %d nie miała nowych linków.", page)
                        continue

                    # Sprawdzenie Tier 0
                    unvisited_urls = []
                    for detail_url in detail_urls:
                        if account and hasattr(account, "id"):
                            if await is_url_visited(detail_url, account.id):
                                continue
                        unvisited_urls.append(detail_url)

                    if not unvisited_urls:
                        logger.info("[BiznesPolska] Wszystkie ogłoszenia na stronie %d były już odwiedzone.", page)
                        continue

                    logger.info("[BiznesPolska] Skanowanie %d nowych ogłoszeń na stronie %d...", len(unvisited_urls), page)
                    
                    candidate_leads = []
                    candidate_urls = []
                    stop_pagination = False

                    # Phase 1: Szybki skan (curl_cffi bez logowania)
                    for detail_url in unvisited_urls:
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        try:
                            detail_resp = await session.get(detail_url, timeout=15)
                            if detail_resp.status_code != 200:
                                continue

                            detail_html = detail_resp.text
                            
                            # Wyciągamy datę publikacji
                            pub_date_str = None
                            pub_match = re.search(r'Data dodania[^:]*:\s*(\d{4}-\d{2}-\d{2})', detail_html, re.IGNORECASE)
                            if not pub_match:
                                # Fallback szukania daty w tekście (YYYY-MM-DD)
                                date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', detail_html)
                                if date_matches:
                                    pub_date_str = date_matches[0]
                            else:
                                pub_date_str = pub_match.group(1)

                            if pub_date_str:
                                try:
                                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                                    if start_dt and pub_date < start_dt:
                                        logger.info(f"[BiznesPolska] Napotkano ogłoszenie starsze niż start_date ({start_date}). Przerywam.")
                                        stop_pagination = True
                                        break
                                except Exception:
                                    pass

                            clean_text = DOMSanitizer.clean(detail_html, max_chars=6000)
                            if len(clean_text) < 50:
                                if account and hasattr(account, "id"):
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            # Keyword check
                            text_lower = clean_text.lower()
                            has_keyword = match_polish_keywords(text_lower, keywords)

                            if not has_keyword:
                                if account and hasattr(account, "id"):
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            # Wyciąganie tytułu
                            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', detail_html, flags=re.DOTALL | re.IGNORECASE)
                            title = re.sub(r'<[^>]+>', "", title_match.group(1)).strip() if title_match else "Ogłoszenie - Biznes Polska"

                            candidate_leads.append({
                                "url": detail_url,
                                "tytul": title,
                                "raw_text": clean_text,
                                "data": pub_date_str if pub_date_str else datetime.utcnow().strftime("%Y-%m-%d")
                            })
                            candidate_urls.append(detail_url)

                        except Exception as e:
                            logger.error("[BiznesPolska] Błąd pobierania Phase 1 %s: %s", detail_url, e)

                    # Phase 2: Pobieranie autoryzowane Playwright
                    if candidate_urls:
                        logger.info("[BiznesPolska] Phase 2: Pobieranie z autoryzacją Playwright dla %d kandydatów...", len(candidate_urls))
                        playwright_results = await fetch_multiple_with_playwright(candidate_urls, user, scraper_password, "BiznesPolska")

                        for lead in candidate_leads:
                            lead_url = lead["url"]
                            auth_html = playwright_results.get(lead_url)

                            if auth_html:
                                logger.info("[BiznesPolska] Pomyślnie pobrano zalogowaną stronę przez Playwright dla %s", lead_url)
                                # Wersja zalogowana zawiera pełne dane kontaktowe w DOM
                                enriched_text = DOMSanitizer.clean(auth_html, max_chars=6000)
                                if len(enriched_text) > len(lead["raw_text"]):
                                    lead["raw_text"] = enriched_text
                            else:
                                logger.warning("[BiznesPolska] Playwright nie pobrał %s, używam fallback z Phase 1", lead_url)

                            raw_items.append(lead)

                    if stop_pagination:
                        return raw_items

                except Exception as page_err:
                    logger.error("[BiznesPolska] Wyjątek podczas skanowania strony %d: %s", page, page_err)

        return raw_items
