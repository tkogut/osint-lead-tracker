"""
osint_engine.py — Silnik AI OSINT z integracją e-Zamówień (BZP REST API) + Google Search Grounding.
Wyszukuje postępowania przetargowe dotyczące wag samochodowych z ostatnich 3 dni roboczych.
"""

import json
import logging
import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import requests
from google import genai
from google.genai import types

from config import get_settings

logger = logging.getLogger(__name__)


def get_date_limits() -> tuple[str, str]:
    """
    Zwraca dzisiejszą datę oraz datę sprzed 3 dni roboczych
    w formacie YYYY-MM-DD (pomijając soboty i niedziele).
    """
    today = datetime.now()
    days_to_subtract = 0
    business_days_subtracted = 0
    while business_days_subtracted < 3:
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


def get_system_instruction(today_str: str, start_str: str) -> str:
    return f"""Jesteś asystentem OSINT / lead research do wykrywania nowych inwestycji i postępowań, w których jedną ze składowych może być:

budowa wagi samochodowej, dostawa nowej wagi samochodowej, montaż i uruchomienie wagi samochodowej, wymiana wagi samochodowej, budowa infrastruktury do ważenia pojazdów, budowa miejsc do ważenia pojazdów, wykonanie fundamentów, infrastruktury technicznej lub oprogramowania związanego z wagą samochodową.

Nie zakładaj, że użytkownik zna nazwę inwestycji, lokalizację, inwestora albo wykonawcę. Twoim zadaniem jest SAMODZIELNIE odnaleźć te dane, aktywnie i cyklicznie korzystając z narzędzia wyszukiwarki (Google Search).

BARDZO WAŻNE (Zakres czasowy i status):
1. Dzisiejsza data (rok 2026) to: {today_str}.
2. Szukamy wyłącznie postępowań opublikowanych w zakresie dat od {start_str} do {today_str}.
3. MASZ ABSOLUTNY ZAKAZ dodawania postępowań, których termin składania ofert już minął, lub które zostały już rozstrzygnięte/unieważnione. Interesują nas wyłącznie AKTYWNE, trwające postępowania. Zawsze sprawdź status i termin składania ofert w treści strony. Kategorycznie odrzuć wyniki, w których przetarg jest oznaczony jako "rozstrzygnięty", "wybrano wykonawcę", "unieważniony", "po terminie".

Zasada formułowania zapytań do wyszukiwarki:
Gdy wywołujesz wyszukiwarkę Google, używaj prostych słów kluczowych (np. "budowa wagi samochodowej przetarg", "waga samochodowa zapytanie ofertowe"). 
BEZWZGLĘDNY ZAKAZ wpisywania w zapytaniach do wyszukiwarki fraz takich jak "data publikacji", "ostatnie 3 dni", czy przedziałów dat typu "2026-07-08..2026-07-13". Wyszukiwarka Google nie rozumie takich filtrów tekstowych i zwraca 0 wyników. Filtrację dat wykonasz samodzielnie na podstawie odczytanej treści stron.

Krytyczna zasada dotycząca linków URL:
W polu "url" musisz podać bezpośredni, oryginalny link publiczny do ogłoszenia na danej platformie (np. https://ezamowienia.gov.pl/..., https://platformazakupowa.pl/..., bip.xxx.pl).
ABSOLUTNY ZAKAZ używania linków przekierowujących z Google Search Grounding (np. zaczynających się od vertexaisearch.cloud.google.com/grounding-api-redirect/...). Wyciągaj bezpośrednie domeny i adresy URL stron źródłowych z tekstu lub z linków w wynikach wyszukiwania.

Cykliczny Algorytm Wyszukiwania (Search Loop):
Masz obowiązek używać narzędzia wyszukiwania w pętli. Nie poddawaj się po pierwszym braku wyników.

Cykl 1 (Zarzucenie sieci): Uruchom wyszukiwarkę dla głównych fraz ogólnych (np. "budowa wagi samochodowej", "waga samochodowa CPV 42923110-6", "wymiana wagi samochodowej na nową").

Ewaluacja: Przeanalizuj zwrócone wyniki. Jeśli brakuje in w nich konkretnych postępowań, nazwy inwestora lub statusu, NIE generuj jeszcze odpowiedzi.

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
                logger.debug("Pominięto lead bez bezpośredniego URL lub z redirectem Google: %s", item.get("tytul"))
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
        self._client = genai.Client(api_key=self._settings.gemini_api_key)

    def _verify_bzp_notice(self, notice: dict) -> dict | None:
        """Weryfikuje treść pojedynczego ogłoszenia z e-Zamówień za pomocą Gemini."""
        html_body = notice.get("htmlBody", "")
        text_content = clean_html(html_body)

        # Lokalny pre-filter słów kluczowych, aby oszczędzić tokeny
        title_lower = notice.get("orderObject", "").lower()
        body_lower = text_content.lower()
        has_keywords = any(k in title_lower or k in body_lower for k in ["waga", "wagi", "wag", "ważeń", "ważen", "scale"])
        is_exact_cpv = "42923110-6" in notice.get("cpvCode", "")

        if not (has_keywords or is_exact_cpv):
            logger.debug("Odrzucono lokalnie ogłoszenie BZP bez słów kluczowych: %s", notice.get("orderObject"))
            return None

        # Ograniczamy treść do 15k znaków
        text_content = text_content[:15000]

        prompt = f"""Przeanalizuj poniższe ogłoszenie o zamówieniu publicznym i określ, czy dotyczy ono wagi samochodowej (wag samochodowych / najazdowych / stanowisk do ważenia pojazdów).

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
2. Jeśli ogłoszenie NIE dotyczy wagi samochodowej (np. dotyczy tylko wag laboratoryjnych, biurowych, wspinaczkowych lub wyłącznie rąbania drewna bez wagi), zwróć wyłącznie słowo: ODRZUĆ.
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
https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/{urllib.parse.quote(notice.get('noticeNumber', ''))}

Zwróć wyłącznie słowo ODRZUĆ lub poprawny format JSON bez znaczników markdown."""

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
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

    def _search_bzp(self, start_date: str, today_date: str) -> list[dict]:
        """Przeszukuje bazę e-Zamówień (BZP API) po kodach CPV wag."""
        logger.info("e-Zamówienia API: start skanowania (%s do %s)…", start_date, today_date)
        cpvs = ["42923110-6", "42923000-2", "42923200-0"]
        url = "https://ezamowienia.gov.pl/mo-board/api/v1/notice"

        found_notices = {}
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
                if r.status_code != 200:
                    logger.warning("Błąd e-Zamówienia API dla CPV %s: %s", cpv, r.status_code)
                    continue

                data = r.json()
                logger.info("Pobrano %d ogłoszeń z e-Zamówień dla CPV %s", len(data), cpv)
                for notice in data:
                    num = notice.get("noticeNumber")
                    if num and num not in found_notices:
                        found_notices[num] = notice
            except Exception as e:
                logger.error("Wyjątek podczas odpytywania e-Zamówień dla CPV %s: %s", cpv, e)

        leads = []
        for num, notice in found_notices.items():
            lead = self._verify_bzp_notice(notice)
            if lead:
                leads.append(lead)

        logger.info("e-Zamówienia API: ukończono. Znaleziono i zweryfikowano %d lead(ów)", len(leads))
        return leads

    def _search_google(self, start_date: str, today_date: str) -> list[dict]:
        """Przeszukuje publiczny internet za pomocą Google Search Grounding."""
        logger.info("Google Search Grounding: start skanowania…")
        instruction = get_system_instruction(today_date, start_date)
        prompt = get_user_prompt(today_date, start_date)

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )

            raw_text = response.text or ""
            logger.debug("Raw AI response (500 chars): %s", raw_text[:500])

            leads = _parse_leads(raw_text)
            logger.info("Google Search Grounding: ukończono. Znaleziono %d lead(ów)", len(leads))
            return leads

        except Exception as exc:
            logger.error("Google Search Grounding FAILED: %s", exc, exc_info=True)
            return []

    def run_search(self) -> list[dict]:
        """
        Uruchamia wyszukiwanie hybrydowe:
        1. Skanowanie bezpośrednie API e-Zamówień (BZP).
        2. Skanowanie szerokie za pomocą Google Search Grounding.
        Merguje i deduplikuje wyniki po URL.
        """
        today_str, start_str = get_date_limits()
        logger.info("OSINT Pipeline START (%s do %s)", start_str, today_str)

        # 1. BZP API
        bzp_leads = self._search_bzp(start_str, today_str)

        # 2. Google Search Grounding
        google_leads = self._search_google(start_str, today_str)

        # Łączenie i deduplikacja
        all_leads = []
        seen_urls = set()

        for lead in bzp_leads + google_leads:
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
