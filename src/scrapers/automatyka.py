"""
automatyka.py — Wtyczka skrapera dla portalu automatyka.pl z omijaniem Cloudflare via curl_cffi i autoryzacją xtech.pl.
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
from scrapers.playwright_fetcher import fetch_with_playwright, fetch_multiple_with_playwright
from src.utils import match_polish_keywords

logger = logging.getLogger(__name__)


def extract_advertiser_info(html_content: str) -> str:
    """
    Wyciąga sekcję 'Dane ogłaszającego' (Nazwa firmy, Osoba kontaktowa, Adres e-mail, Nr telefonu, Adres do kontaktu)
    z surowego HTML portalu Automatyka.pl / Xtech.pl.
    """
    extracted_lines = []

    block_match = re.search(
        r'(?:Dane\s+ogłaszającego|Dane\s+kontaktowe|Kontakt\s+do\s+ogłoszeniodawcy)(.*?)(?:</section>|</aside>|<div\s+class="[^"]*description[^"]*">|<h\d|$)',
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )
    if not block_match:
        return ""
    search_scope = block_match.group(1)

    # Nazwa firmy
    firm_m = re.search(r'(?:Nazwa\s+firmy|Firma|Firma/Instytucja)[^:]*:\s*(?:<[^>]+>\s*)*([^<\r\n]+)', search_scope, re.IGNORECASE)
    if firm_m:
        firm = firm_m.group(1).strip()
        if firm:
            extracted_lines.append(f"Nazwa firmy: {firm}")

    # Osoba kontaktowa
    cp_m = re.search(r'(?:Osoba\s+kontaktowa|Kontakt|Osoba\s+do\s+kontaktu)[^:]*:\s*(?:<[^>]+>\s*)*([^<\r\n]+)', search_scope, re.IGNORECASE)
    if cp_m:
        cp = cp_m.group(1).strip()
        if cp:
            extracted_lines.append(f"Osoba kontaktowa: {cp}")

    # Adres e-mail
    email_m = re.search(r'(?:Adres\s+e-mail|E-mail|Email)[^:]*:\s*(?:<[^>]+>\s*)*([\w\.-]+@[\w\.-]+\.\w+)', search_scope, re.IGNORECASE)
    if email_m:
        em = email_m.group(1).strip()
        if em:
            extracted_lines.append(f"Adres e-mail: {em}")
    else:
        all_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', search_scope)
        for e in all_emails:
            if not any(d in e.lower() for d in ["automatyka.pl", "xtech.pl", "example.com", "schema.org"]):
                extracted_lines.append(f"Adres e-mail: {e.strip()}")
                break

    # Nr telefonu
    phone_m = re.search(r'(?:Nr\s+telefonu|Telefon|Tel\.?)[^:]*:\s*(?:<[^>]+>\s*)*([\+\d\s\-\(\)]{7,})', search_scope, re.IGNORECASE)
    if phone_m:
        ph = phone_m.group(1).strip()
        if ph:
            extracted_lines.append(f"Nr telefonu: {ph}")

    # Adres do kontaktu
    addr_m = re.search(r'(?:Adres\s+do\s+kontaktu|Adres)[^:]*:\s*(?:<[^>]+>\s*)*([^<\r\n]+)', search_scope, re.IGNORECASE)
    if addr_m:
        addr = addr_m.group(1).strip()
        if addr:
            extracted_lines.append(f"Adres do kontaktu: {addr}")

    if extracted_lines:
        return "=== DANE OGŁASZAJĄCEGO ===\n" + "\n".join(extracted_lines) + "\n===========================\n\n"
    elif block_match:
        clean_block = re.sub(r'<[^>]+>', ' ', block_match.group(1))
        clean_block = " ".join(clean_block.strip().split())
        if len(clean_block) > 5:
            return f"=== DANE OGŁASZAJĄCEGO ===\n{clean_block}\n===========================\n\n"
    return ""


def parse_notice_detail(detail_html: str, detail_url: str = "") -> Dict[str, Any]:
    """
    Parsuje szczegóły ogłoszenia/zapytania z portalu Automatyka.pl.
    Obsługuje standardowe ogłoszenia oraz podstrony zbiorcze marek i kategorii (np. -27, ?topId=...).
    """
    top_id = None
    if detail_url:
        top_id_m = re.search(r'[?&]topId=(\d+)', detail_url)
        if top_id_m:
            top_id = top_id_m.group(1)

    # Sprawdzenie czy w treści występują kafelki box-styles
    box_matches = list(re.finditer(r'<div[^>]*class="[^"]*box-styles[^"]*"[^>]*>', detail_html, flags=re.IGNORECASE))

    # Strona zbiorcza (gdy są kafelki box-styles)
    if box_matches:
        boxes = []
        for i, m in enumerate(box_matches):
            start = m.start()
            if i + 1 < len(box_matches):
                end = box_matches[i + 1].start()
            else:
                cutoff_m = re.search(r'(?:<footer|<aside|<div\s+class="[^"]*pagination|<div\s+class="[^"]*footer)', detail_html[start:], re.IGNORECASE)
                if cutoff_m:
                    end = start + cutoff_m.start()
                else:
                    end = len(detail_html)
            boxes.append(detail_html[start:end])

        target_box = None
        # Jeśli mamy top_id, szukamy kafelka z tym numerem
        if top_id:
            for b in boxes:
                if re.search(rf"Zapytanie\s+nr\s+{top_id}\b", b, re.IGNORECASE) or re.search(rf"\b{top_id}\b", b):
                    target_box = b
                    break

        # Fallback: kafelek aktywny
        if not target_box:
            for b in boxes:
                if re.search(r'class="[^"]*\bactive\b[^"]*"', b, re.IGNORECASE):
                    target_box = b
                    break

        # Fallback: pierwszy kafelek
        if not target_box and boxes:
            target_box = boxes[0]

        if target_box:
            # 1. Tytuł z <h2> wewnątrz tego kafelka, fallback do <h1>
            title = None
            h2_m = re.search(r'<h2[^>]*>(.*?)</h2>', target_box, flags=re.DOTALL | re.IGNORECASE)
            if h2_m:
                h2_text = re.sub(r'<[^>]+>', '', h2_m.group(1)).strip()
                if h2_text:
                    title = h2_text

            if not title:
                h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', detail_html, flags=re.DOTALL | re.IGNORECASE)
                if h1_m:
                    title = re.sub(r'<[^>]+>', '', h1_m.group(1)).strip()

            if not title:
                title = "Zapytanie ofertowe - Automatyka.pl"

            # 2. Data publikacji z <small>Opublikowano: ...</small> wewnątrz tego kafelka
            pub_date_str = None
            small_pub_m = re.search(r'<small[^>]*>Opublikowano:\s*(\d{4}-\d{2}-\d{2})</small>', target_box, re.IGNORECASE)
            if small_pub_m:
                pub_date_str = small_pub_m.group(1)
            else:
                box_pub_m = re.search(r'Opublikowano:\s*(\d{4}-\d{2}-\d{2})', target_box, re.IGNORECASE)
                if box_pub_m:
                    pub_date_str = box_pub_m.group(1)
                else:
                    box_date_m = re.search(r'z\s+dnia\s+(\d{4}-\d{2}-\d{2})', target_box, re.IGNORECASE)
                    if box_date_m:
                        pub_date_str = box_date_m.group(1)

            # 3. Wyizolowanie tekstu tego konkretnego zapytania
            clean_text = DOMSanitizer.clean(target_box, max_chars=6000)

            return {
                "title": title,
                "pub_date_str": pub_date_str,
                "clean_text": clean_text
            }

    # Standardowe ogłoszenie (brak kafelków box-styles)
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", detail_html, flags=re.DOTALL | re.IGNORECASE)
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else "Zapytanie ofertowe - Automatyka.pl"

    pub_date_str = None
    pub_match = re.search(r"Opublikowano:\s*(\d{4}-\d{2}-\d{2})", detail_html, re.IGNORECASE)
    if pub_match:
        pub_date_str = pub_match.group(1)
    else:
        fallback_match = re.search(r"z\s+dnia\s+(\d{4}-\d{2}-\d{2})", detail_html, re.IGNORECASE)
        if fallback_match:
            pub_date_str = fallback_match.group(1)

    clean_text = DOMSanitizer.clean(detail_html, max_chars=6000)

    return {
        "title": title,
        "pub_date_str": pub_date_str,
        "clean_text": clean_text
    }


class AutomatykaScraper(BaseScraper):
    """
    Dedykowany skraper dla portalu automatyka.pl (zapytania ofertowe).
    """
    parse_notice_detail = staticmethod(parse_notice_detail)

    def __init__(self) -> None:
        super().__init__(source_name="Automatyka")
        self.base_url = "https://www.automatyka.pl/zapytania-ofertowe"

    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        raw_items: List[Dict[str, Any]] = []

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            today_dt = datetime.strptime(today_date, "%Y-%m-%d").date()
            search_window_days = (today_dt - start_dt).days
        except Exception as date_err:
            logger.warning("[Automatyka] Blad parsowania start_date (%s) lub today_date (%s): %s", start_date, today_date, date_err)
            search_window_days = 7
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception:
                start_dt = None

        keywords = ["waga", "wagi", "wag", "ważeń", "ważen", "najazd"]
        if hasattr(account, "target_keywords") and account.target_keywords:
            try:
                import json
                parsed_kws = json.loads(account.target_keywords)
                if parsed_kws:
                    keywords = [k.lower().strip() for k in parsed_kws]
            except Exception:
                pass

        user = get_db_setting_sync("SCRAPER_AUTOMATYKA_USER", "")
        scraper_password = get_db_setting_sync("SCRAPER_AUTOMATYKA_PASS", "")

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
            "Referer": "https://www.automatyka.pl/",
        }

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            if user and scraper_password:
                try:
                    logger.info("[Automatyka] Autoryzacja w xtech.pl dla użytkownika: %s", user)
                    login_resp = await session.post(
                        "https://www.xtech.pl/zaloguj",
                        json={"LoginName": user, "Password": scraper_password, "Step": 1, "ServiceId": 3},
                        timeout=15
                    )
                    logger.info("[Automatyka] Status autoryzacji w xtech.pl: %s", login_resp.status_code)
                except Exception as login_err:
                    logger.error("[Automatyka] Błąd logowania do xtech.pl: %s", login_err)

            for page in range(1, 11):
                url = self.base_url if page == 1 else f"{self.base_url}?page={page}"
                try:
                    logger.info("[Automatyka] Pobieranie listy zapytań ofertowych ze strony %d: %s...", page, url)
                    resp = await session.get(url, timeout=15)
                    
                    if resp.status_code != 200:
                        logger.warning("[Automatyka] Nieprawidłowy status HTTP na stronie %d: %s", page, resp.status_code)
                        continue

                    html = resp.text
                    if "Just a moment..." in html or "Cloudflare" in html and resp.status_code == 403:
                        logger.error("[Automatyka] Wykryto blokadę Cloudflare / Captcha na stronie %d!", page)
                        continue

                    # Ekstrakcja unikalnych linków do ogłoszeń z listy
                    found_links = set(re.findall(r'href=["\'](/zapytania-ofertowe/[^"\']+)["\']', html))
                    detail_urls = []
                    for link in found_links:
                        # Match notice links ending with -ID1-ID2 pattern or brand/category pages like -ID or containing query params
                        if re.match(r'^/zapytania-ofertowe/[^/:\?]+-(?:\d+-\d+|\d+)(?:\?.*)?$', link):
                            full_url = urllib.parse.urljoin(self.base_url, link)
                            detail_urls.append(full_url)

                    if not detail_urls:
                        logger.info("[Automatyka] Strona %d nie miała nowych linków.", page)
                        continue

                    # Sprawdzenie Tier 0 dla wszystkich url na tej stronie
                    unvisited_urls = []
                    for detail_url in detail_urls:
                        if account and hasattr(account, "id"):
                            if await is_url_visited(detail_url, account.id):
                                continue
                        unvisited_urls.append(detail_url)

                    if not unvisited_urls:
                        logger.info("[Automatyka] Wszystkie ogłoszenia na stronie %d były już odwiedzone. Przechodzę do następnej strony.", page)
                        continue

                    logger.info("[Automatyka] Znaleziono %d nowych linków ogłoszeń na stronie %d.", len(unvisited_urls), page)

                    candidate_leads = []
                    candidate_urls = []
                    stop_pagination = False

                    # Phase 1: Quick scanning via curl_cffi (no login)
                    for detail_url in unvisited_urls:
                        # Jitter opóźnienia rate limiting
                        await asyncio.sleep(random.uniform(0.8, 2.2))

                        try:
                            logger.info("[Automatyka] Phase 1: Szybkie pobieranie %s przez curl_cffi...", detail_url)
                            detail_resp = await session.get(detail_url, timeout=15)
                            
                            if detail_resp.status_code != 200:
                                logger.warning("[Automatyka] Błąd pobierania %s: status %s", detail_url, detail_resp.status_code)
                                continue

                            detail_html = detail_resp.text

                            notice_data = parse_notice_detail(detail_html, detail_url)
                            pub_date_str = notice_data["pub_date_str"]
                            clean_text = notice_data["clean_text"]
                            title = notice_data["title"]

                            if pub_date_str:
                                try:
                                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                                    if start_dt and pub_date < start_dt:
                                        logger.info(f"[Automatyka] Napotkano ogłoszenie starsze niż start_date ({start_date}). Przerywam paginację.")
                                        stop_pagination = True
                                        break
                                except Exception as parse_pub_err:
                                    logger.warning("[Automatyka] Błąd parsowania wyciągniętej daty %s: %s", pub_date_str, parse_pub_err)

                            if len(clean_text) < 50:
                                logger.warning("[Automatyka] Odrzucono zbyt krótki tekst po sanitacji DOM: %s", detail_url)
                                if account and hasattr(account, "id"):
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            # Sprawdzenie słów kluczowych pre-filter
                            text_lower = clean_text.lower()
                            has_keyword = match_polish_keywords(text_lower, keywords)

                            if not has_keyword:
                                logger.debug("[Automatyka] Brak słów kluczowych w %s (SKIPPED pre-filter)", detail_url)
                                if account and hasattr(account, "id"):
                                    await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                                continue

                            candidate_leads.append({
                                "url": detail_url,
                                "tytul": title,
                                "raw_text": clean_text,
                                "data": pub_date_str if pub_date_str else datetime.utcnow().strftime("%Y-%m-%d"),
                            })
                            candidate_urls.append(detail_url)

                        except Exception as detail_err:
                            logger.error("[Automatyka] Błąd skanowania szczegółów Phase 1 %s: %s", detail_url, detail_err)

                    # Phase 2: Playwright fetch for candidates to get contact details
                    if candidate_urls:
                        logger.info("[Automatyka] Phase 2: Pobieranie z autoryzacją Playwright dla %d kandydatów...", len(candidate_urls))
                        playwright_results = await fetch_multiple_with_playwright(candidate_urls, user, scraper_password, "Automatyka")
                        
                        for lead in candidate_leads:
                            lead_url = lead["url"]
                            authenticated_html = playwright_results.get(lead_url)
                            
                            if authenticated_html:
                                logger.info("[Automatyka] Pomyślnie pobrano dane kontaktowe przez Playwright dla %s", lead_url)
                                contact_header = extract_advertiser_info(authenticated_html)
                                if contact_header:
                                    lead["raw_text"] = contact_header + lead["raw_text"]
                            else:
                                logger.warning("[Automatyka] Playwright nie zdołał pobrać %s, używam fallback z Phase 1", lead_url)
                            
                            raw_items.append(lead)
                            logger.info("[Automatyka] Dodano nową ofertę: %s", lead["tytul"])

                    if stop_pagination:
                        return raw_items

                except Exception as page_err:
                    logger.error("[Automatyka] Wyjątek podczas skanowania strony %d: %s", page, page_err)

        return raw_items
