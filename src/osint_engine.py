"""
osint_engine.py — Silnik AI OSINT z integracją e-Zamówień (BZP API), Google Search Grounding oraz pozwoleń na budowę (GUNB RWDZ).
Wyszukuje postępowania przetargowe i decyzje budowlane dotyczące wag samochodowych z ostatnich 3 dni roboczych.
Umożliwia parametryzację LLM i filtrów wyszukiwania per konto (Account).
"""

import csv
import json
import logging
import os
import re
import urllib.parse
import zipfile
import io
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple, List

import requests
from google import genai
from google.genai import types

from config import get_settings
from database import get_db_setting_sync, is_url_visited, mark_url_visited
from scrapers.factory import get_scraper_for_source, SCRAPER_REGISTRY
import asyncio

logger = logging.getLogger(__name__)


def get_date_limits(default_days: int = 7) -> tuple[str, str]:
    """
    Zwraca dzisiejszą datę oraz datę sprzed N dni roboczych (domyślnie 7)
    w formacie YYYY-MM-DD (pomijając soboty i niedziele).
    """
    try:
        window_days = int(get_db_setting_sync("SEARCH_WINDOW_DAYS", str(default_days)))
    except Exception:
        window_days = default_days

    today = datetime.now()
    days_to_subtract = 0
    business_days_subtracted = 0
    while business_days_subtracted < window_days:
        days_to_subtract += 1
        day = today - timedelta(days=days_to_subtract)
        if day.weekday() < 5:
            business_days_subtracted += 1

    start_date = today - timedelta(days=days_to_subtract)
    return today.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d")


def clean_html(raw_html: str) -> str:
    """Usuwa znaczniki HTML i encje, zwracając czysty tekst."""
    if not raw_html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def format_prompt_dates(prompt_text: str, today_str: str, start_str: str) -> str:
    """Dynamically replaces hardcoded old date strings in system prompts."""
    if not prompt_text:
        return prompt_text
    
    # "Dzisiejsza data (rok 2026) to: YYYY-MM-DD" -> with current today_str
    prompt_text = re.sub(
        r"Dzisiejsza data \(rok \d{4}\) to: \d{4}-\d{2}-\d{2}",
        f"Dzisiejsza data (rok {today_str[:4]}) to: {today_str}",
        prompt_text
    )
    
    # "od YYYY-MM-DD do YYYY-MM-DD" -> with start_str..today_str
    prompt_text = re.sub(
        r"od \d{4}-\d{2}-\d{2} do \d{4}-\d{2}-\d{2}",
        f"od {start_str} do {today_str}",
        prompt_text
    )
    
    return prompt_text


def get_system_instruction(today_str: str, start_str: str) -> str:
    return f"""Jesteś asystentem OSINT / lead research do wykrywania nowych inwestycji i postępowań, w których jedną ze składowych może być:

budowa wagi samochodowej, dostawa nowej wagi samochodowej, montaż i uruchomienie wagi samochodowej, wymiana wagi samochodowej, budowa infrastruktury do ważenia pojazdów, budowa miejsc do ważenia pojazdów, wykonanie fundamentów, infrastruktury technicznej lub oprogramowania związanego z wagą samochodową.

Nie zakładaj, że użytkownik zna nazwę inwestycji, lokalizację, inwestora albo wykonawcę. Twoim zadaniem jest SAMODZIELNIE odnaleźć te dane, aktywnie i cyklicznie korzystając z narzędzia wyszukiwarki (Google Search).

Kryterium Tematyczne (GŁÓWNE): Jeśli treść dotyczy tematyki kampanii (np. wzorcowanie wag, zakup z wzorcowaniem, legalizacja, serwis), treść JEST wartościowym leadem.

Reguła braku dat: Brak jawnej daty publikacji lub terminu składania ofert w surowej treści NIE MOŻE powodować odrzucenia leada (ODRZUĆ / empty json). Jeśli brak dat w tekście, załóż status AKTYWNY.

OBSŁUGA STRON ZBIORCZYCH I WIELOKROTNYCH ZAPYTAŃ:
1. Przekazana treść może stanowić stronę zbiorczą, zestawienie kategorialne lub agregator zapytań zawierający wiele różnych produktów lub usług.
2. Przeszukaj cały tekst i WYEKSTRAHUJ WSZYSTKIE POJEDYNCZE OGŁOSZENIA/ZAPYTANIA, których treść ściśle odpowiada wymaganiom kampanii zdefiniowanym w system_instruction.
3. Ignoruj wszelkie inne wpisy, produkty i ogłoszenia w tekście, które NIE ODPOWIADAJĄ kryteriom kampanii.
4. Zwróć każdy pasujący lead w strukturze JSON. Jeśli żaden wpis w tekście nie odpowiada wymaganiom kampanii, zwróć tablicę {{"leady": []}}.

Gradacja Priorytetu:
- wysoki: Pełne dane (jawna data ofert, inwestor, szczegółowy zakres).
- sredni: Jasny zakres i kontakt, drobne braki.
- niski: Krótkie/proste zapytanie lub brak jawnego terminu ofert, ale treść odpowiada tematyce kampanii.

BARDZO WAŻNE (Zakres czasowy i status):
1. Dzisiejsza data (rok 2026) to: {today_str}.
2. Szukamy wyłącznie postępowań opublikowanych w zakresie dat od {start_str} do {today_str}.
3. MASZ ABSOLUTNY ZAKAZ dodawania postępowań, których termin składania ofert już minął, lub które zostały już rozstrzygnięte/unieważnione. Interesują nas wyłącznie AKTYWNE, trwające postępowania. Zawsze sprawdź status i termin składania ofert w treści strony. Kategorycznie odrzuć wyniki, w których przetarg jest oznaczony jako "rozstrzygnięty", "wybrano wykonawcę", "unieważniony", "po terminie".
4. Status i termin dla skraperów: Jeśli w surowej treści ogłoszenia brak podanego dokładnego terminu składania ofert, ale data opublikowania/wygenerowania mieści się w wyznaczonym oknie czasowym (od {start_str} do {today_str}), załóż że ogłoszenie jest AKTYWNE (trwające) i nie odrzucaj go z powodu braku jawnego terminu.

Ekstrakcja Inwestora: Jeśli nazwa zamawiającego nie występuje bezpośrednio w nagłówku, WYCIĄGNIJ ją z kontekstu treści (np. nazwa zakładu produkcyjnego, fabryki, inwestora, kompleksu, oddziału spółki, np. Zakład Produkcyjny 'Pomorze' i 'Mazowsze').

Zasada formułowania zapytań do wyszukiwarki:
Gdy wywołujesz wyszukiwarkę Google, używaj prostych słów kluczowych (np. "budowa wagi samochodowej przetarg", "waga samochodowa zapytanie ofertowe"). 
BEZWZGLĘDNY ZAKAZ wpisywania w zapytaniach do wyszukiwarki fraz takich jak "data publikacji", "ostatnie 3 dni", czy przedziałów dat typu "2026-07-08..2026-07-13". Wyszukiwarka Google nie rozumie takich filtrów tekstowych i zwraca 0 wyników. Filtrację dat wykonasz samodzielnie na podstawie odczytanej treści stron.

Krytyczna zasada dotycząca linków URL:
W polu "url" musisz podać bezpośredni, oryginalny link publiczny do ogłoszenia na danej platformie (np. https://ezamowienia.gov.pl/..., https://platformazakupowa.pl/..., bip.xxx.pl).
ABSOLUTNY ZAKAZ używania linków przekierowujących z Google Search Grounding (np. zaczynających się od vertexaisearch.cloud.google.com/grounding-api-redirect/...). Wyciągaj bezpośrednie domeny i adresy URL stron źródłowych z tekstu lub z linków w wynikach wyszukiwania.

Cykliczny Algorytm Wyszukiwania (Search Loop):
Masz obowiązek używać narzędzia wyszukiwania w pętli. Nie poddawaj się po pierwszym braku wyników.

Cykl 1 (Zarzucenie sieci): Uruchom wyszukiwarkę dla głównych fraz ogólnych (np. "budowa wagi samochodowej", "waga samochodowa CPV 42923110-6", "wymiana wagi samochodowej na nową").

Cykl 2 (Precyzowanie): Uruchom narzędzie wyszukiwania ponownie, celując w konkretne platformy i typy zapytań (np. site:ezamowienia.gov.pl "waga najazdowa", site:platformazakupowa.pl "infrastruktura do ważenia", "waga samochodowa" "zapytanie ofertowe").

Cykl 3 (Deep Dive): Jeśli znalazłeś inwestycję, ale brakuje danych o wykonawcy lub lokalizacji, uruchom wyszukiwanie celowane pod nazwę tej konkretnej inwestycji, aby uzupełnić luki.

Warunek zakończenia: Zakończ pętlę i przejdź do raportowania dopiero, gdy uzyskasz kompletne dane do wygenerowania struktury leadu lub wyczerpiesz ścieżki poszukiwań.

Sposób działania i obszar skanowania:
Przeszukuj: platformy przetargowe, BIP, eZamówienia, platformazakupowa, portale branżowe, agregatory przetargów, strony inwestorów oraz media regionalne. Z każdego źródła wyciągnij: nazwę inwestycji, lokalizację, zamawiającego, wykonawcę, zakres dotyczący wagi, status, datę publikacji, link źródłowy, priorytet.

WARUNEK KRYTYCZNY (Zero halucynacji & Format JSON):
If po przejściu całej pętli nie znajdziesz twardych, weryfikowalnych, aktywnych postępowań opublikowanych w okresie od {start_str} do {today_str} z fizycznym adresem URL, ZWRÓĆ PUSTĄ TABLICĘ {{"leady": []}}. Masz absolutny zakaz generowania danych demonstracyjnych i mock-upów.
Odpowiedź MUSI być czystym formatem JSON bez znaczników markdown. Struktura:
{{"leady": [{{"tytul": "...", "typ": "...", "nazwa_inwestycji": "...", "lokalizacja": "...", "inwestor": "...", "wykonawca": "...", "zakres": "...", "uzasadnienie": "...", "priorytet": "wysoki/sredni/niski", "data": "...", "url": "..."}}]}}"""


def get_user_prompt(today_str: str, start_str: str) -> str:
    return (
        f"Uruchom pełną pętlę wyszukiwania OSINT dla aktywnych postępowań opublikowanych "
        f"w zakresie od {start_str} do {today_str} dotyczących wag samochodowych. "
        f"Upewnij się, że terminy składania ofert nie minęły, a przetargi nie są rozstrzygnięte. "
        f"Zwróć wyłącznie oryginalne, bezpośrednie adresy URL (nie linki vertexaisearch). Zwróć czysty JSON bez markdown."
    )


def _strip_markdown_fences(text: str) -> str:
    """Usuwa ewentualne znaczniki ```json ... ``` z odpowiedzi LLM."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_leads(raw_text: str) -> list[dict]:
    """
    Parsuje surową odpowiedź LLM do listy leadów.
    Przy błędzie parsowania zwraca [].
    """
    if not raw_text or not raw_text.strip():
        logger.warning("Pusta odpowiedź z modelu AI.")
        return []
    clean = _strip_markdown_fences(raw_text)
    try:
        payload: Any = json.loads(clean)
        if isinstance(payload, dict):
            leads = payload.get("leady", [])
        elif isinstance(payload, list):
            leads = payload
        else:
            logger.warning("Nieoczekiwany typ JSON: %s", type(payload))
            leads = []

        valid = []
        for item in leads:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "").strip()
            if not url or url in ("...", "N/A", "") or "grounding-api-redirect" in url or "vertexaisearch" in url:
                logger.debug("Pominięto lead bez bezpośredniego URL: %s", item.get("tytul"))
                continue
            valid.append(item)

        logger.info("Sparsowano %d lead(ów) z odpowiedzi AI", len(valid))
        return valid

    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s | raw=%s", exc, clean[:500])
        return []


class OSINTEngine:
    """Główna klasa silnika OSINT."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _verify_bzp_notice(self, notice: dict, account: Optional[Any] = None) -> dict | None:
        """Weryfikuje treść pojedynczego ogłoszenia z e-Zamówień za pomocą Gemini."""
        html_body = notice.get("htmlBody", "")
        text_content = clean_html(html_body)

        title_lower = notice.get("orderObject", "").lower()
        body_lower = text_content.lower()

        # Konfiguracja słów kluczowych i CPV
        keywords = ["waga", "wagi", "wag", "ważeń", "ważen", "scale"]
        if account:
            try:
                acc_kws = json.loads(account.target_keywords)
                if acc_kws:
                    keywords = [k.lower().strip() for k in acc_kws]
            except Exception:
                pass

        cpvs = ["42923110-6", "42923000-2", "42923200-0"]
        if account:
            try:
                acc_cpvs = json.loads(account.target_cpvs)
                if acc_cpvs:
                    cpvs = [c.strip() for c in acc_cpvs]
            except Exception:
                pass

        has_keywords = any(k in title_lower or k in body_lower for k in keywords)
        is_exact_cpv = any(c in notice.get("cpvCode", "") for c in cpvs)

        if not (has_keywords or is_exact_cpv):
            logger.debug("Odrzucono lokalnie ogłoszenie BZP bez słów kluczowych: %s", notice.get("orderObject"))
            return None

        text_content = text_content[:15000]

        custom_prompt = ""
        if account and account.custom_prompt:
            today_str, start_str = get_date_limits()
            formatted_prompt = format_prompt_dates(account.custom_prompt, today_str, start_str)
            custom_prompt = formatted_prompt + "\n\n"

        if account and account.custom_prompt:
            # Custom campaigns prompt
            prompt = f"""{custom_prompt}Przeanalizuj poniższe ogłoszenie o zamówieniu publicznym i określ, czy odpowiada ono powyższym wymaganiom.

Szczegóły ogłoszenia:
- Tytuł: {notice.get('orderObject')}
- Organizacja: {notice.get('organizationName')} ({notice.get('organizationCity')})
- CPV: {notice.get('cpvCode')}
- Numer: {notice.get('noticeNumber')}

Treść ogłoszenia:
\"\"\"
{text_content}
\"\"\"

Wymagania:
1. Zdecyduj, czy ogłoszenie jest wartościowym leadem zgodnie ze zdefiniowanymi powyżej kryteriami kampanii.
2. Jeśli ogłoszenie NIE spełnia kryteriów kampanii, zwróć wyłącznie słowo: ODRZUĆ.
3. Jeśli ogłoszenie spełnia kryteria, zwróć dane leada w formacie JSON zgodnym ze strukturą opisaną powyżej.
Zwróć wyłącznie słowo ODRZUĆ lub poprawny format JSON bez znaczników markdown."""
        else:
            # Default prompt for car scales (Wagi Samochodowe)
            prompt = f"""Przeanalizuj poniższe ogłoszenie o zamówieniu publicznym i określ, czy dotyczy ono wagi samochodowej (wag samochodowych / najazdowych / stanowisk do ważenia pojazdów) lub odpowiada zdefiniowanym wymaganiom.

Szczegóły ogłoszenia:
- Tytuł: {notice.get('orderObject')}
- Organizacja: {notice.get('organizationName')} ({notice.get('organizationCity')})
- CPV: {notice.get('cpvCode')}
- Numer: {notice.get('noticeNumber')}

Treść ogłoszenia:
\"\"\"
{text_content}
\"\"\"

Wymagania:
1. Zdecyduj, czy w przedmiocie zamówienia pojawia się konieczność dostawy, zakupu, montażu, modernizacji, fundamentów lub legalizacji wagi samochodowej (dla pojazdów ciężarowych/dostawczych).
2. Jeśli ogłoszenie NIE dotyczy wagi samochodowej, zwróć wyłącznie słowo: ODRZUĆ.
3. Jeśli dotyczy wagi samochodowej, zwróć dane leada w formacie JSON o poniższej strukturze:
{{
  "tytul": "Tytuł ogłoszenia",
  "typ": "lead",
  "nazwa_inwestycji": "Nazwa inwestycji/zamówienia",
  "lokalizacja": "Miasto, województwo, adres",
  "inwestor": "Nazwa zamawiającego",
  "wykonawca": "",
  "zakres": "Krótki opis zakresu dotyczący wagi samochodowej (np. dostawa wagi najazdowej 60t, wykonanie fundamentu)",
  "uzasadnienie": "Dlaczego to ogłoszenie jest wartościowym leadem",
  "priorytet": "wysoki/sredni/niski",
  "data": "Data publikacji w formacie YYYY-MM-DD",
  "url": "Bezpośredni link do ogłoszenia"
}}
W polu 'url' użyj dokładnie tego wzorca, wstawiając numer ogłoszenia {notice.get('noticeNumber')}:
https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/{urllib.parse.quote(notice.get('noticeNumber', ''), safe='')}

Zwróć wyłącznie słowo ODRZUĆ lub poprawny format JSON bez znaczników markdown."""

        llm_model = "gemini-2.5-flash"
        llm_temp = 0.1
        if account:
            llm_model = account.llm_model
            llm_temp = account.llm_temperature

        api_key = get_db_setting_sync("GEMINI_API_KEY", self._settings.gemini_api_key)
        client = genai.Client(api_key=api_key)

        try:
            response = client.models.generate_content(
                model=llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=llm_temp,
                ),
            )
            ans = (response.text or "").strip()
            if ans == "ODRZUĆ" or "ODRZUĆ" in ans[:20]:
                logger.debug("AI odrzuciło ogłoszenie BZP: %s", notice.get("orderObject"))
                return None

            clean_json = _strip_markdown_fences(ans)
            lead_data = json.loads(clean_json)
            logger.info("AI zweryfikowało i zaakceptowało ogłoszenie BZP jako lead: %s", lead_data.get("tytul"))
            return lead_data
        except Exception as exc:
            logger.error("Błąd podczas weryfikacji ogłoszenia BZP %s: %s", notice.get("noticeNumber"), exc)
            return None

    def _extract_lead_from_raw_text(
        self,
        text_content: str,
        source_url: str,
        account: Optional[Any] = None
    ) -> Tuple[Optional[dict], int, int]:
        """
        Zleca Gemini wyciągnięcie ustrukturyzowanych danych leada z oczyszczonego surowego tekstu ogłoszenia
        pobranego przez wtyczkę skrapera (bez zapytań wyszukiwarki / Search Grounding).
        Zwraca (lead_dict, input_tokens, output_tokens).
        """
        if not text_content or len(text_content.strip()) < 50:
            return None, 0, 0

        today_str, start_str = get_date_limits()
        custom_prompt = ""
        if account and account.custom_prompt:
            formatted_prompt = format_prompt_dates(account.custom_prompt, today_str, start_str)
            custom_prompt = formatted_prompt + "\n\n"

        prompt = f"""{custom_prompt}Przeanalizuj poniższy tekst ogłoszenia/zapytania ofertowego ze strony: {source_url}

Treść ogłoszenia:
\"\"\"
{text_content}
\"\"\"

Wymagania:
1. Kryterium Tematyczne (GŁÓWNE): Jeśli treść dotyczy tematyki kampanii (np. wzorcowanie wag, zakup z wzorcowaniem, legalizacja, serwis), treść JEST wartościowym leadem.
2. OBSŁUGA STRON ZBIORCZYCH I WIELOKROTNYCH ZAPYTAŃ:
   - Przekazana treść może stanowić stronę zbiorczą, zestawienie kategorialne lub agregator zapytań zawierający wiele różnych produktów lub usług.
   - Przeszukaj cały tekst i WYEKSTRAHUJ WSZYSTKIE POJEDYNCZE OGŁOSZENIA/ZAPYTANIA, których treść ściśle odpowiada wymaganiom kampanii zdefiniowanym w system_instruction.
   - Ignoruj wszelkie inne wpisy, produkty i ogłoszenia w tekście, które NIE ODPOWIADAJĄ kryteriom kampanii.
   - Zwróć każdy pasujący lead w strukturze JSON. Jeśli żaden wpis w tekście nie odpowiada wymaganiom kampanii, zwróć tablicę {{"leady": []}}.
3. Reguła braku dat: Brak jawnej daty publikacji lub terminu składania ofert w surowej treści NIE MOŻE powodować odrzucenia leada (ODRZUĆ / empty json). Jeśli brak dat w tekście, załóż status AKTYWNY.
4. Gradacja Priorytetu:
   - wysoki: Pełne dane (jawna data ofert, inwestor, szczegółowy zakres).
   - sredni: Jasny zakres i kontakt, drobne braki.
   - niski: Krótkie/proste zapytanie lub brak jawnego terminu ofert, ale treść odpowiada tematyce kampanii.
5. Ekstrakcja Inwestora: Jeśli nazwa zamawiającego nie występuje bezpośrednio w nagłówku, WYCIĄGNIJ ją z kontekstu treści (np. nazwa zakładu produkcyjnego, fabryki, inwestora, kompleksu, oddziału spółki, np. Zakład Produkcyjny 'Pomorze' i 'Mazowsze').
6. Jeśli treść NIE zawiera żadnego zapytania spełniającego wymagania tematyczne kampanii lub minął jawnie podany termin, zwróć wyłącznie słowo: ODRZUĆ.
7. Jeśli ogłoszenie spełnia kryteria, zwróć dane wszystkich dopasowanych leadów w formacie JSON w strukturze {{"leady": [...]}} z elementami o poniższej strukturze:
{{
  "tytul": "Tytuł ogłoszenia / zapytania",
  "typ": "lead",
  "nazwa_inwestycji": "Nazwa inwestycji",
  "lokalizacja": "Lokalizacja (miasto, województwo)",
  "inwestor": "Nazwa zamawiającego / inwestora",
  "wykonawca": "",
  "zakres": "Opis zakresu przedmiotu zamówienia",
  "uzasadnienie": "Dlaczego to ogłoszenie jest wartościowym leadem",
  "priorytet": "wysoki/sredni/niski",
  "data": "Data publikacji lub obecna YYYY-MM-DD",
  "url": "{source_url}"
}}

Zwróć wyłącznie słowo ODRZUĆ lub poprawny format JSON bez znaczników markdown."""

        llm_model = "gemini-2.5-flash"
        llm_temp = 0.1
        if account:
            llm_model = account.llm_model
            llm_temp = account.llm_temperature

        api_key = get_db_setting_sync("GEMINI_API_KEY", self._settings.gemini_api_key)
        client = genai.Client(api_key=api_key)

        try:
            response = client.models.generate_content(
                model=llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=llm_temp,
                ),
            )

            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

            ans = (response.text or "").strip()
            if ans == "ODRZUĆ" or "ODRZUĆ" in ans[:20]:
                logger.debug("AI odrzuciło tekst ogłoszenia ze źródła %s", source_url)
                return None, input_tokens, output_tokens

            clean_json = _strip_markdown_fences(ans)
            payload = json.loads(clean_json)
            extracted = []
            if isinstance(payload, dict):
                if "leady" in payload and isinstance(payload["leady"], list):
                    extracted = payload["leady"]
                else:
                    extracted = [payload]
            elif isinstance(payload, list):
                extracted = payload

            valid_leads = []
            for item in extracted:
                if isinstance(item, dict):
                    item["url"] = source_url
                    valid_leads.append(item)

            if not valid_leads:
                return None, input_tokens, output_tokens

            logger.info("AI wyekstrahowało %d lead(ów) z surowego tekstu (%s)", len(valid_leads), source_url)
            return valid_leads, input_tokens, output_tokens
        except Exception as exc:
            logger.error("Błąd ekstrakcji leada z tekstu (%s): %s", source_url, exc)
            return None, 0, 0

    def _search_plugin(
        self,
        source_name: str,
        start_date: str,
        today_date: str,
        account: Any
    ) -> Tuple[List[dict], int, str, int, int, int, int]:
        """Uruchamia dedykowaną wtyczkę skrapera oraz dokonuje ekstrakcji danych z surowego tekstu via Gemini."""
        scraper = get_scraper_for_source(source_name)
        if not scraper:
            logger.warning("Brak zarejestrowanej wtyczki skrapera dla źródła: %s", source_name)
            return [], 404, hashlib.sha256(b"not_found").hexdigest(), 0, 0, 0, 0

        logger.info("[%s Plugin] Start skanowania dla konta %s…", source_name, account.name)

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                raw_items = loop.run_until_complete(scraper.fetch_leads(account, start_date, today_date))
            else:
                raw_items = asyncio.run(scraper.fetch_leads(account, start_date, today_date))
        except Exception as exc:
            logger.error("[%s Plugin] Wyjątek podczas uruchamiania skrapera: %s", source_name, exc, exc_info=True)
            err_hash = hashlib.sha256(str(exc).encode("utf-8")).hexdigest()
            return [], 500, err_hash, 0, 0, 0, 0

        leads = []
        total_input_tokens = 0
        total_output_tokens = 0
        combined_payload = ""

        for item in raw_items:
            url = item.get("url", "").strip()
            raw_text = item.get("raw_text", "").strip()
            if not url or not raw_text:
                continue

            combined_payload += f"{url}:{len(raw_text)}\n"
            lead, in_tok, out_tok = self._extract_lead_from_raw_text(raw_text, url, account=account)
            total_input_tokens += in_tok
            total_output_tokens += out_tok

            if lead:
                if isinstance(lead, list):
                    leads.extend(lead)
                else:
                    leads.append(lead)
                if hasattr(account, "id"):
                    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                    try:
                        if loop and loop.is_running():
                            loop.run_until_complete(mark_url_visited(url, account.id, source_name, content_hash=content_hash, status="PROCESSED"))
                        else:
                            asyncio.run(mark_url_visited(url, account.id, source_name, content_hash=content_hash, status="PROCESSED"))
                    except Exception:
                        pass

        response_hash = hashlib.sha256(combined_payload.encode("utf-8")).hexdigest() if combined_payload else hashlib.sha256(b"empty").hexdigest()
        logger.info("[%s Plugin] Ukończono. Znaleziono %d surowych ogłoszeń, wyekstrahowano %d lead(ów)", source_name, len(raw_items), len(leads))
        return leads, 200, response_hash, 0, 0, total_input_tokens, total_output_tokens


    def _search_bzp(self, start_date: str, today_date: str, account: Optional[Any] = None) -> Tuple[List[dict], int, str, int, int, int, int]:
        """Przeszukuje bazę e-Zamówień (BZP API)."""
        logger.info("e-Zamówienia API: start skanowania (%s do %s)…", start_date, today_date)
        
        cpvs = ["42923110-6", "42923000-2", "42923200-0"]
        if account:
            try:
                acc_cpvs = json.loads(account.target_cpvs)
                if acc_cpvs:
                    cpvs = [c.strip() for c in acc_cpvs]
            except Exception:
                pass
                
        url = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"

        found_notices = {}
        combined_responses = b""
        last_status_code = 200

        for cpv in cpvs:
            try:
                params = {
                    "PageSize": 100,
                    "PublicationDateFrom": start_date,
                    "PublicationDateTo": today_date,
                    "NoticeType": "ContractNotice",
                    "CpvCode": cpv,
                }
                r = requests.get(url, params=params, timeout=15)
                last_status_code = r.status_code
                if r.status_code != 200:
                    logger.warning("Błąd e-Zamówienia API dla CPV %s: %s", cpv, r.status_code)
                    continue

                combined_responses += r.content
                data = r.json()
                logger.info("Pobrano %d ogłoszeń z e-Zamówień dla CPV %s", len(data), cpv)
                for notice in data:
                    num = notice.get("noticeNumber")
                    if num and num not in found_notices:
                        found_notices[num] = notice
            except Exception as e:
                logger.error("Wyjątek podczas odpytywania e-Zamówień dla CPV %s: %s", cpv, e)
                last_status_code = 500

        leads = []
        for num, notice in found_notices.items():
            lead = self._verify_bzp_notice(notice, account=account)
            if lead:
                leads.append(lead)

        response_hash = hashlib.sha256(combined_responses).hexdigest()
        logger.info("e-Zamówienia API: ukończono. Znaleziono i zweryfikowano %d lead(ów)", len(leads))
        return leads, last_status_code, response_hash, 0, 0, 0, 0

    def _search_google(self, start_date: str, today_date: str, account: Optional[Any] = None) -> Tuple[List[dict], int, str, int, int, int, int]:
        """Przeszukuje publiczny internet za pomocą Google Search Grounding."""
        logger.info("Google Search Grounding: start skanowania…")
        
        llm_model = "gemini-2.5-flash"
        llm_temp = 0.1
        llm_max_tokens = 8192
        instruction = get_system_instruction(today_date, start_date)

        if account:
            llm_model = account.llm_model
            llm_temp = account.llm_temperature
            llm_max_tokens = account.llm_max_tokens
            if account.custom_prompt:
                instruction = format_prompt_dates(account.custom_prompt, today_date, start_date)

        keywords_str = "wagach samochodowych"
        if account:
            try:
                acc_kws = json.loads(account.target_keywords)
                if acc_kws:
                    keywords_str = ", ".join(acc_kws)
            except Exception:
                pass

        prompt = (
            f"Uruchom pełną pętlę wyszukiwania OSINT dla aktywnych postępowań opublikowanych "
            f"w zakresie od {start_date} do {today_date} dotyczących: {keywords_str}. "
            f"Upewnij się, że terminy składania ofert nie minęły, a przetargi nie są rozstrzygnięte. "
            f"Zwróć wyłącznie oryginalne, bezpośrednie adresy URL (nie linki vertexaisearch). Zwróć czysty JSON bez markdown."
        )

        api_key = get_db_setting_sync("GEMINI_API_KEY", self._settings.gemini_api_key)
        client = genai.Client(api_key=api_key)

        try:
            response = client.models.generate_content(
                model=llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=llm_temp,
                    max_output_tokens=llm_max_tokens,
                ),
            )

            raw_text = response.text or ""
            leads = _parse_leads(raw_text)
            response_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            # Extract grounding metadata and token usage
            grounding_chunks = 0
            grounding_queries = 0
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                gm = getattr(candidate, 'grounding_metadata', None)
                if gm:
                    chunks = getattr(gm, 'grounding_chunks', []) or []
                    grounding_chunks = len(chunks)
                    queries = getattr(gm, 'web_search_queries', []) or []
                    grounding_queries = len(queries)

            logger.info(
                "Google Search Grounding: ukończono. Znaleziono %d lead(ów), chunks=%d, queries=%d, in_tok=%d, out_tok=%d",
                len(leads), grounding_chunks, grounding_queries, input_tokens, output_tokens
            )
            return leads, 200, response_hash, grounding_chunks, grounding_queries, input_tokens, output_tokens

        except Exception as exc:
            logger.error("Google Search Grounding FAILED: %s", exc, exc_info=True)
            err_hash = hashlib.sha256(str(exc).encode("utf-8")).hexdigest()
            return [], 500, err_hash, 0, 0, 0, 0

    def _search_gunb(self, start_date: str, today_date: str, account: Optional[Any] = None) -> Tuple[List[dict], int, str, int, int, int, int]:
        """
        Pobiera i analizuje rejestr pozwoleń na budowę RWDZ (GUNB).
        """
        logger.info("GUNB RWDZ: start skanowania (%s do %s)…", start_date, today_date)
        
        cache_path = "./data/gunb_cache.json"
        cache = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cache = json.load(f)
            except Exception as e:
                logger.error("Błąd ładowania pamięci podręcznej GUNB: %s", e)

        pobranie_url = "https://wyszukiwarka.gunb.gov.pl/pobranie.html"
        last_status_code = 200
        combined_headers = ""

        # Słowa kluczowe do filtrowania pozwoleń
        keywords = ["waga", "wagi", "wag"]
        exact_keywords = ["samochod", "najazd", "ciężar"]

        if account:
            try:
                acc_kws = json.loads(account.target_keywords)
                if acc_kws:
                    keywords = [k.lower().strip() for k in acc_kws]
                    exact_keywords = [""]  # Elastyczny filtr jednowarstwowy
            except Exception:
                pass

        try:
            r = requests.get(pobranie_url, timeout=15)
            last_status_code = r.status_code
            if r.status_code != 200:
                logger.error("Błąd pobierania strony GUNB: %s", r.status_code)
                err_hash = hashlib.sha256(f"status_{r.status_code}".encode("utf-8")).hexdigest()
                return [], r.status_code, err_hash, 0, 0, 0, 0
            
            links = re.findall(r'href="([^"]+\.zip)"', r.text)
        except Exception as e:
            logger.error("Wyjątek podczas pobierania strony GUNB: %s", e)
            err_hash = hashlib.sha256(str(e).encode("utf-8")).hexdigest()
            return [], 500, err_hash, 0, 0, 0, 0

        leads = []
        updated_cache = {}

        for link in links:
            if "wynik_zgloszenia_2016_2021" in link:
                continue
                
            full_url = link if link.startswith("http") else "https://wyszukiwarka.gunb.gov.pl/" + link
            filename = os.path.basename(link)

            try:
                head = requests.head(full_url, timeout=5)
                content_length = head.headers.get("Content-Length", "")
                last_modified = head.headers.get("Last-Modified", "")
                combined_headers += f"{filename}:{content_length}:{last_modified}\n"
            except Exception as e:
                logger.warning("Błąd odpytywania nagłówków dla %s: %s", filename, e)
                content_length = ""

            cached_len = cache.get(filename)
            updated_cache[filename] = content_length

            if cached_len and cached_len == content_length:
                logger.debug("Plik %s jest aktualny (pomijam pobieranie)", filename)
                continue

            logger.info("Pobieranie i analiza aktualizacji rejestru GUNB: %s (rozmiar: %s bajtów)...", filename, content_length)
            
            try:
                res = requests.get(full_url, timeout=30)
                if res.status_code != 200:
                    logger.warning("Nie udało się pobrać %s: %s", filename, res.status_code)
                    continue

                with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                    csv_name = [f for f in z.namelist() if f.endswith(".csv")]
                    if not csv_name:
                        continue
                    
                    with z.open(csv_name[0]) as csv_file:
                        wrapper = io.TextIOWrapper(csv_file, encoding="utf-8-sig")
                        reader = csv.reader(wrapper, delimiter=";")
                        
                        header = next(reader, None)
                        if not header:
                            continue
                            
                        obj_idx = -1
                        date_decyzja_idx = -1
                        date_wplyw_idx = -1
                        city_idx = -1
                        org_idx = -1
                        gunb_idx = -1
                        organ_idx = -1
                        woj_idx = -1
                        
                        for idx, col in enumerate(header):
                            col_lower = col.lower()
                            if "numer_gunb" in col_lower: gunb_idx = idx
                            elif "nazwa_organu" in col_lower: organ_idx = idx
                            elif "data_wplywu_wniosku" in col_lower: date_wplyw_idx = idx
                            elif "data_wydania_decyzji" in col_lower: date_decyzja_idx = idx
                            elif "nazwa_inwestor" in col_lower: org_idx = idx
                            elif "miasto" in col_lower: city_idx = idx
                            elif "wojewodztwo" in col_lower: woj_idx = idx
                            elif "nazwa_zam_budowlanego" in col_lower or "nazwa_zamierzenia_bud" in col_lower:
                                if obj_idx == -1: obj_idx = idx

                        for row in reader:
                            if len(row) < max(gunb_idx, organ_idx, date_wplyw_idx, date_decyzja_idx, org_idx, city_idx, woj_idx, obj_idx) + 1:
                                continue
                            
                            data_decyzji = row[date_decyzja_idx].strip() if date_decyzja_idx != -1 else ""
                            data_wplywu = row[date_wplyw_idx].strip() if date_wplyw_idx != -1 else ""
                            
                            date_str = None
                            if data_decyzji:
                                date_str = data_decyzji[:10]
                            elif data_wplywu:
                                date_str = data_wplywu[:10]
                                
                            if not date_str or not (start_date <= date_str <= today_date):
                                continue

                            nazwa_zamierzenia = row[obj_idx].strip() if obj_idx != -1 else ""
                            inwestor = row[org_idx].strip() if org_idx != -1 else ""
                            
                            text_search = (nazwa_zamierzenia + " " + inwestor).lower()
                            
                            match_keyword = any(k in text_search for k in keywords)
                            match_exact = any(e in text_search for e in exact_keywords)
                            
                            if match_keyword and match_exact:
                                numer_gunb = row[gunb_idx].strip() if gunb_idx != -1 else "brak_nr"
                                nazwa_organu = row[organ_idx].strip() if organ_idx != -1 else ""
                                city = row[city_idx].strip() if city_idx != -1 else ""
                                woj = row[woj_idx].strip() if woj_idx != -1 else ""
                                campaign_name = account.name if account else "Budowa wagi samochodowej"
                                lead_data = {
                                    "url": f"https://wyszukiwarka.gunb.gov.pl/wniosek/{urllib.parse.quote(numer_gunb, safe='')}",
                                    "tytul": f"{campaign_name} - {inwestor or 'Inwestor prywatny'}",
                                    "typ": "lead",
                                    "lokalizacja": f"{city}, woj. {woj}".strip(", "),
                                    "inwestor": inwestor or "Inwestor prywatny (dane w rejestrze RWDZ)",
                                    "wykonawca": "",
                                    "zakres": nazwa_zamierzenia,
                                    "uzasadnienie": f"Wpis w rejestrze pozwoleń na budowę GUNB RWDZ (numer GUNB: {numer_gunb}). Wydający organ: {nazwa_organu}.",
                                    "priorytet": "wysoki",
                                    "data": date_str
                                }
                                leads.append(lead_data)
                                logger.info("Wykryto pozwolenie na budowę z rejestru GUNB: %s", lead_data["tytul"])
            
            except Exception as e:
                logger.error("Błąd podczas przetwarzania pliku GUNB %s: %s", filename, e)

        try:
            with open(cache_path, "w") as f:
                json.dump(updated_cache, f)
        except Exception as e:
            logger.error("Błąd zapisu pamięci podręcznej GUNB: %s", e)

        response_hash = hashlib.sha256(combined_headers.encode("utf-8")).hexdigest()
        logger.info("GUNB RWDZ: ukończono. Wykryto %d nowych lead(ów)", len(leads))
        return leads, last_status_code, response_hash, 0, 0, 0, 0

    def run_search_for_account(
        self,
        account: Any
    ) -> dict[str, tuple[list[dict], int, str, int, int, int, int]]:
        """Uruchamia wyszukiwanie dla konkretnego konta/kampanii."""
        today_str, start_str = get_date_limits()
        logger.info("OSINT Account Search START for '%s' (%s do %s)", account.name, start_str, today_str)

        enabled_sources = ["BZP", "Google", "GUNB"]
        if hasattr(account, "enabled_sources") and account.enabled_sources:
            try:
                if isinstance(account.enabled_sources, str):
                    parsed = json.loads(account.enabled_sources)
                else:
                    parsed = account.enabled_sources
                if isinstance(parsed, list) and len(parsed) > 0:
                    enabled_sources = parsed
            except Exception:
                pass

        results = {}

        for source in enabled_sources:
            if source == "BZP":
                results["BZP"] = self._search_bzp(start_str, today_str, account=account)
            elif source == "Google":
                results["Google"] = self._search_google(start_str, today_str, account=account)
            elif source == "GUNB":
                results["GUNB"] = self._search_gunb(start_str, today_str, account=account)
            else:
                # Dedykowane wtyczki skraperów (np. Automatyka)
                results[source] = self._search_plugin(source, start_str, today_str, account=account)

        return results

    def run_search(self) -> list[dict]:
        """Fallback kompatybilności wstecznej dla starszych skryptów."""
        today_str, start_str = get_date_limits()
        logger.info("OSINT Pipeline START (%s do %s)", start_str, today_str)

        bzp_leads, _, _, _, _, _, _ = self._search_bzp(start_str, today_str)
        google_leads, _, _, _, _, _, _ = self._search_google(start_str, today_str)
        gunb_leads, _, _, _, _, _, _ = self._search_gunb(start_str, today_str)

        # Łączenie i deduplikacja
        all_leads = []
        seen_urls = set()

        for lead in bzp_leads + google_leads + gunb_leads:
            url = lead.get("url", "").strip()
            if not url:
                continue
            if url not in seen_urls:
                seen_urls.add(url)
                all_leads.append(lead)

        logger.info("OSINT Pipeline DONE. Łącznie po deduplikacji: %d lead(ów)", len(all_leads))
        return all_leads


# Singleton
_engine: OSINTEngine | None = None


def get_engine() -> OSINTEngine:
    global _engine
    if _engine is None:
        _engine = OSINTEngine()
    return _engine
