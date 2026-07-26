# Plan 043: Integracja skrapera Baza Konkurencyjności (BK2021)

Ten plan opisuje wdrożenie nowej wtyczki skrapera dla portalu **Baza Konkurencyjności** (`bazakonkurencyjnosci.funduszeeuropejskie.gov.pl`). Na podstawie analizy ruchu sieciowego zidentyfikowaliśmy asynchroniczne, publiczne API, które pozwala na pobranie pełnych danych (w tym danych kontaktowych i opisu) w formacie JSON bez logowania i bez konieczności uruchamiania Playwright.

---

## Cel wdrożenia
Dodanie obsługi serwisu Baza Konkurencyjności jako dedykowanego źródła OSINT:
1. Pobieranie listy najnowszych ogłoszeń z publicznego endpointu API wyszukiwarki:
   `https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/search?page={page}&limit=20&sort=publication_date_desc&status%5B0%5D=PUBLISHED`
2. Sprawdzenie daty publikacji ogłoszenia (`publication_date`) i przerwanie paginacji, jeśli ogłoszenie jest starsze niż `start_date`.
3. Szybkie filtrowanie słów kluczowych na poziomie listy (`title` i `content`).
4. Dla pasujących ogłoszeń – pobranie pełnych danych szczegółowych, w tym danych kontaktowych, z asynchronicznego API szczegółów:
   `https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/{id}`
5. Pełna integracja z panelem Dashboard, Rejestrem Logów oraz piaskownicą (Sandbox) bez wymogu podawania credentials (dane logowania nie są wymagane).

---

## Proponowane Zmiany

### 1. Nowa wtyczka skrapera
#### [NEW] [baza_konkurenconosci.py](file:///home/tkogut/projects/osint-lead-tracker/src/scrapers/baza_konkurenconosci.py)
Tworzymy wtyczkę `BazaKonkurenconosciScraper` dziedziczącą z `BaseScraper`. Proces pobierania będzie w pełni jednofazowy (`curl_cffi`):

```python
"""
baza_konkurenconosci.py — Wtyczka skrapera dla portalu Baza Konkurencyjności (BK2021) w oparciu o REST API.
"""

import asyncio
import logging
import random
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any

from curl_cffi.requests import AsyncSession
from scrapers.base import BaseScraper, DOMSanitizer
from database import is_url_visited, mark_url_visited

logger = logging.getLogger("osint.scraper.baza_konkurenconosci")


class BazaKonkurenconosciScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(source_name="BazaKonkurenconosci")
        self.search_url = "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/search"
        self.details_base = "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/"

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
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/szukaj",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        }

        async with AsyncSession(impersonate="chrome124", headers=headers) as session:
            for page in range(1, 11):
                url = f"{self.search_url}?page={page}&limit=20&sort=publication_date_desc&status%5B0%5D=PUBLISHED"
                try:
                    logger.info("[BazaKonkurenconosci] Pobieranie listy ze strony %d: %s...", page, url)
                    resp = await session.get(url, timeout=15)
                    if resp.status_code != 200:
                        logger.warning("[BazaKonkurenconosci] Nieprawidłowy status HTTP: %s", resp.status_code)
                        continue

                    json_data = resp.json()
                    advs = json_data.get("data", {}).get("advertisements", [])
                    if not advs:
                        logger.info("[BazaKonkurenconosci] Strona %d nie zawiera ogłoszeń.", page)
                        break

                    stop_pagination = False
                    for adv in advs:
                        adv_id = adv.get("id")
                        if not adv_id:
                            continue

                        detail_url = f"https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/{adv_id}"
                        
                        # Sprawdzenie daty publikacji
                        pub_date_str = adv.get("publication_date")
                        if pub_date_str:
                            try:
                                # Format YYYY-MM-DD
                                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                                if start_dt and pub_date < start_dt:
                                    logger.info(f"[BazaKonkurenconosci] Napotkano ogłoszenie starsze niż start_date ({start_date}). Przerywam.")
                                    stop_pagination = True
                                    break
                            except Exception:
                                pass

                        # Sprawdzenie Tier 0
                        if account and hasattr(account, "id"):
                            if await is_url_visited(detail_url, account.id):
                                continue

                        # Szybki Keyword filter
                        title = adv.get("title", "")
                        snippet = adv.get("content", "")
                        combined_list_text = f"{title} {snippet}".lower()
                        
                        has_keyword = any(k in combined_list_text for k in keywords) if keywords else True
                        if not has_keyword:
                            if account and hasattr(account, "id"):
                                await mark_url_visited(detail_url, account.id, self.source_name, status="SKIPPED")
                            continue

                        # Pasujące ogłoszenie -> pobranie pełnych szczegółów z API (w tym danych kontaktowych)
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        api_detail_url = f"{self.details_base}{adv_id}"
                        try:
                            logger.info("[BazaKonkurenconosci] Pobieranie szczegółów z API dla ogłoszenia %s...", adv_id)
                            det_resp = await session.get(api_detail_url, timeout=15)
                            if det_resp.status_code != 200:
                                continue

                            det_data = det_resp.json().get("data", {}).get("advertisement", {})
                            
                            # Budowanie surowego tekstu z pól JSON do parsowania przez AI
                            # Dane kontaktowe
                            contacts_text = ""
                            contacts = det_data.get("contact_persons", [])
                            for c in contacts:
                                name = f"{c.get('forename', '')} {c.get('surname', '')}".strip()
                                phone = c.get("phone_number", "")
                                email = c.get("email", "")
                                contacts_text += f"\nOsoba kontaktowa: {name}, tel: {phone}, email: {email}"

                            # Opis i przedmioty zamówienia
                            orders_text = ""
                            orders = det_data.get("orders", [])
                            for o in orders:
                                for item in o.get("order_items", []):
                                    desc = item.get("description", "")
                                    orders_text += f"\nPrzedmiot zamówienia: {desc}"

                            # Scalenie
                            full_raw_content = f"""
Tytuł: {det_data.get('title', title)}
Ogłoszeniodawca: {adv.get('advertiser_name', '')}
Numer ogłoszenia: {det_data.get('advertisement', {}).get('number', '')}
Miejsce realizacji: {adv.get('fulfillment_place', '')}
Termin składania ofert: {det_data.get('submission_deadline', '')}
Dane kontaktowe: {contacts_text}
Opis zamówienia: {orders_text}
                            """

                            clean_text = DOMSanitizer.clean(full_raw_content, max_chars=6000)
                            
                            raw_items.append({
                                "url": detail_url,
                                "tytul": title,
                                "raw_text": clean_text,
                                "data": pub_date_str if pub_date_str else datetime.utcnow().strftime("%Y-%m-%d")
                            })

                        except Exception as det_err:
                            logger.error("[BazaKonkurenconosci] Błąd szczegółów %s: %s", adv_id, det_err)

                    if stop_pagination:
                        break

                except Exception as page_err:
                    logger.error("[BazaKonkurenconosci] Wyjątek na stronie %d: %s", page, page_err)

        return raw_items
```

---

### 2. Rejestracja wtyczki
#### [MODIFY] [factory.py](file:///home/tkogut/projects/osint-lead-tracker/src/scrapers/factory.py)
Dodamy `BazaKonkurenconosciScraper` do rejestru wtyczek:

```python
from scrapers.baza_konkurenconosci import BazaKonkurenconosciScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "Automatyka": AutomatykaScraper,
    "Logintrade": LogintradeScraper,
    "BiznesPolska": BiznesPolskaScraper,
    "BazaKonkurenconosci": BazaKonkurenconosciScraper,
}
```

---

### 3. Integracja z panelem i Sandboxem
#### [MODIFY] [main.py](file:///home/tkogut/projects/osint-lead-tracker/src/main.py)
1. W `/api/sources` zarejestrujemy nowe źródło:
```python
        {"id": "BazaKonkurenconosci", "name": "Baza Konkurencyjności (Fundusze UE)", "description": "Publiczny portal zapytań ofertowych w projektach unijnych. Brak logowania.", "is_plugin": True}
```

2. W `sandbox_fetch_url()` i `run_sandbox_test()` obsłużymy pobieranie z logiką Bazy Konkurencyjności (BK2021). Jeśli URL zawiera `bazakonkurencyjnosci.funduszeeuropejskie.gov.pl`, przepiszemy żądanie szczegółów na asynchroniczny endpoint API szczegółów i pobierzemy dane w formacie JSON bezpośrednio za pomocą `curl_cffi` (bez Playwright!):
```python
        elif "bazakonkurencyjnosci.funduszeeuropejskie.gov.pl" in req.url:
            # Wyciągamy ID ze ścieżki /ogloszenia/{id}
            match = re.search(r"/ogloszenia/(\d+)", req.url)
            if match:
                adv_id = match.group(1)
                api_url = f"https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/{adv_id}"
                async with CffiAsyncSession(impersonate="chrome124") as s:
                    r = await s.get(api_url, timeout=15)
                    # formatowanie JSON do tekstu jak we wtyczce...
```

#### [MODIFY] [index.html](file:///home/tkogut/projects/osint-lead-tracker/src/static/index.html)
Dodamy `"BazaKonkurenconosci"` do listy wyboru scrapera w zakładce Sandbox.

---

## Plan Weryfikacji

### Testy Automatyczne
1. Napiszemy testy jednostkowe `tests/test_baza_konkurenconosci.py` symulujące API wyszukiwania i API szczegółów.
2. Uruchomienie testów:
   ```bash
   PYTHONPATH=src .venv/bin/python -m unittest tests/test_baza_konkurenconosci.py
   ```

### Weryfikacja Ręczna (z udziałem Użytkownika)
1. W zakładce Sandbox wklejamy link np. `https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/ogloszenia/251593`, wybieramy kontekst `"Auto (Wykryj automatycznie)"` i weryfikujemy, czy pobrany tekst zawiera pełne dane kontaktowe.
