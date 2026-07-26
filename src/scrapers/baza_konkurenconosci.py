"""
baza_konkurenconosci.py — Wtyczka skrapera dla Baza Konkurencyjności.
"""

import json
import logging
from typing import List, Dict, Any
from curl_cffi.requests import AsyncSession

from scrapers.base import BaseScraper, DOMSanitizer
from database import is_url_visited, mark_url_visited

logger = logging.getLogger(__name__)


class BazaKonkurenconosciScraper(BaseScraper):
    def __init__(self):
        super().__init__("BazaKonkurenconosci")

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_name}] Rozpoczęto pobieranie (Data od: {start_date} do {today_date})...")
        raw_items = []
        
        keywords = []
        if account and hasattr(account, "target_keywords"):
            try:
                if isinstance(account.target_keywords, str):
                    keywords = json.loads(account.target_keywords)
                else:
                    keywords = account.target_keywords
            except Exception:
                pass
        keywords_lower = [k.lower() for k in keywords] if keywords else []

        async with AsyncSession(impersonate="chrome124") as session:
            for page in range(1, 11):
                list_url = f"https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/search?page={page}&limit=20&sort=publication_date_desc&status%5B0%5D=PUBLISHED"
                
                try:
                    response = await session.get(list_url)
                    response.raise_for_status()
                    data = response.json()
                    advertisements = data.get("data", {}).get("advertisements", [])
                except Exception as e:
                    logger.error(f"[{self.source_name}] Błąd podczas pobierania strony {page}: {e}")
                    break

                if not advertisements:
                    break

                stop_pagination = False
                for ad in advertisements:
                    pub_date = ad.get("publication_date", "")[:10]  # get YYYY-MM-DD
                    if pub_date < start_date:
                        stop_pagination = True
                        break

                    ad_id = ad.get("id")
                    if not ad_id:
                        continue

                    url = f"https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/{ad_id}"
                    
                    if account and hasattr(account, "id"):
                        if await is_url_visited(url, account.id):
                            continue

                    title = ad.get("title", "")
                    content = ad.get("content", "")
                    combined_text = (title + " " + content).lower()
                    
                    match_found = False
                    if not keywords_lower:
                        match_found = True
                    else:
                        for kw in keywords_lower:
                            if kw in combined_text:
                                match_found = True
                                break
                                
                    if not match_found:
                        if account and hasattr(account, "id"):
                            await mark_url_visited(url, account.id, self.source_name, status="SKIPPED")
                        continue

                    detail_url = f"https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/{ad_id}"
                    try:
                        detail_resp = await session.get(detail_url)
                        detail_resp.raise_for_status()
                        detail_data = detail_resp.json()
                        adv_details = detail_data.get("data", {}).get("advertisement", {})
                        
                        contact_persons = adv_details.get("contact_persons", [])
                        orders = adv_details.get("orders", [])
                        
                        details_text = f"Title: {title}\nDescription: {content}\n\nContact Persons:\n"
                        for cp in contact_persons:
                            details_text += f"- {cp.get('forename', '')} {cp.get('surname', '')} | Phone: {cp.get('phone_number', '')} | Email: {cp.get('email', '')}\n"
                        
                        details_text += "\nOrders:\n"
                        for order in orders:
                            for item in order.get("order_items", []):
                                details_text += f"- {item.get('description', '')}\n"
                                
                        clean_text = DOMSanitizer.clean(details_text)
                        
                        raw_items.append({
                            "url": url,
                            "tytul": title,
                            "raw_text": clean_text,
                            "data": pub_date
                        })
                    except Exception as e:
                        logger.error(f"[{self.source_name}] Błąd podczas pobierania szczegółów {detail_url}: {e}")

                if stop_pagination:
                    break

        return raw_items
