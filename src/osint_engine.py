"""
osint_engine.py — Silnik AI OSINT z Google Gemini 2.5 Flash + Search Grounding.
Wyszukuje postępowania przetargowe dotyczące wag samochodowych z ostatnich 3 dni roboczych.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any

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
        # weekday(): 0 = poniedziałek, ..., 4 = piątek, 5 = sobota, 6 = niedziela
        if day.weekday() < 5:
            business_days_subtracted += 1

    start_date = today - timedelta(days=days_to_subtract)
    return today.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d")


def get_system_instruction(today_str: str, start_str: str) -> str:
    return f"""Jesteś asystentem OSINT / lead research do wykrywania nowych inwestycji i postępowań, w których jedną ze składowych może być:

budowa wagi samochodowej, dostawa nowej wagi samochodowej, montaż i uruchomienie wagi samochodowej, wymiana wagi samochodowej, budowa infrastruktury do ważenia pojazdów, budowa miejsc do ważenia pojazdów, wykonanie fundamentów, infrastruktury technicznej lub oprogramowania związanego z wagą samochodową.

Nie zakładaj, że użytkownik zna nazwę inwestycji, lokalizację, inwestora albo wykonawcę. Twoim zadaniem jest SAMODZIELNIE odnaleźć te dane, aktywnie i cyklicznie korzystając z narzędzia wyszukiwarki (Google Search).

BARDZO WAŻNE (Zakres czasowy i status):
1. Dzisiejsza data (rok 2026) to: {today_str}.
2. Szukamy wyłącznie postępowań opublikowanych w zakresie dat od {start_str} do {today_str}.
3. MASZ ABSOLUTNY ZAKAZ dodawania postępowań, których termin składania ofert już minął, lub które zostały już rozstrzygnięte/unieważnione. Interesują nas wyłącznie AKTYWNE, trwające postępowania. Zawsze sprawdź status i termin składania ofert w treści strony.

Krytyczna zasada dotycząca linków URL:
W polu "url" musisz podać bezpośredni, oryginalny link publiczny do ogłoszenia na danej platformie (np. https://ezamowienia.gov.pl/..., https://platformazakupowa.pl/..., bip.xxx.pl).
ABSOLUTNY ZAKAZ używania linków przekierowujących z Google Search Grounding (np. zaczynających się od vertexaisearch.cloud.google.com/grounding-api-redirect/...). Wyciągaj bezpośrednie domeny i adresy URL stron źródłowych.

Cykliczny Algorytm Wyszukiwania (Search Loop):
Masz obowiązek używać narzędzia wyszukiwania w pętli. Nie poddawaj się po pierwszym braku wyników.

Cykl 1 (Zarzucenie sieci): Uruchom wyszukiwarkę dla głównych fraz ogólnych (np. "budowa wagi samochodowej", "waga samochodowa CPV 42923110-6", "wymiana wagi samochodowej na nową" po {start_str}).

Ewaluacja: Przeanalizuj zwrócone wyniki. Jeśli brakuje in w nich konkretnych postępowań, nazwy inwestora lub statusu, NIE generuj jeszcze odpowiedzi.

Cykl 2 (Precyzowanie): Uruchom narzędzie wyszukiwania ponownie, celując w konkretne platformy i typy zapytań (np. site:ezamowienia.gov.pl "waga najazdowa" po {start_str}, site:platformazakupowa.pl "infrastruktura do ważenia" po {start_str}, "waga samochodowa" "zapytanie ofertowe" po {start_str}).

Cykl 3 (Deep Dive): Jeśli znalazłeś inwestycję, ale brakuje danych o wykonawcy lub lokalizacji, uruchom wyszukiwanie celowane pod nazwę tej konkretnej inwestycji, aby uzupełnić luki.

Warunek zakończenia: Zakończ pętlę i przejdź do raportowania dopiero, gdy uzyskasz kompletne dane do wygenerowania struktury leadu lub wyczerpiesz ścieżki poszukiwań.

Sposób działania i obszar skanowania:
Przeszukuj: platformy przetargowe, BIP, eZamówienia, platformazakupowa, portale branżowe, agregatory przetargów, strony inwestorów oraz media regionalne. Z każdego źródła wyciągnij: nazwę inwestycji, lokalizację, zamawiającego, wykonawcę, zakres dotyczący wagi, status, datę publikacji, link źródłowy, priorytet.

WARUNEK KRYTYCZNY (Zero halucynacji & Format JSON):
Jeśli po przejściu całej pętli nie znajdziesz twardych, weryfikowalnych, aktywnych postępowań opublikowanych w okresie od {start_str} do {today_str} z fizycznym adresem URL, ZWRÓĆ PUSTĄ TABLICĘ {{"leady": []}}. Masz absolutny zakaz generowania danych demonstracyjnych i mock-upów.
Odpowiedź MUSI być czystym formatem JSON bez znaczników markdown. Struktura:
{{"leady": [{{"tytul": "...", "typ": "...", "nazwa_inwestycji": "...", "lokalizacja": "...", "inwestor": "...", "wykonawca": "...", "zakres": "...", "uzasadnienie": "...", "priorytet": "wysoki/sredni/niski", "data": "...", "url": "..."}}]}}"""


def get_user_prompt(today_str: str, start_str: str) -> str:
    return (
        f"Uruchom pełną pętlę wyszukiwania OSINT dla aktywnych postępowań opublikowanych "
        f"w zakresie od {start_str} do {today_str} dotyczących wag samochodowych. "
        f"Upewnij się, że terminy składania ofert nie minęły. Zwróć wyłącznie oryginalne, "
        f"bezpośrednie adresy URL źródeł (nie linki vertexaisearch). Zwróć czysty JSON bez markdown."
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
            if not url or url in ("...", "N/A", "") or "grounding-api-redirect" in url:
                logger.debug("Pominięto lead bez bezpośredniego URL lub z redirectem: %s", item.get("tytul"))
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

    def run_search(self) -> list[dict]:
        """
        Uruchamia wyszukiwanie OSINT przy użyciu Gemini 2.5 Flash
        z Google Search Grounding.
        """
        today_str, start_str = get_date_limits()
        logger.info("OSINT Engine: start wyszukiwania (%s do %s)…", start_str, today_str)

        instruction = get_system_instruction(today_str, start_str)
        prompt = get_user_prompt(today_str, start_str)

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
            logger.info("OSINT Engine: znaleziono %d lead(ów)", len(leads))
            return leads

        except Exception as exc:
            logger.error("OSINT Engine FAILED: %s", exc, exc_info=True)
            return []


# Singleton
_engine: OSINTEngine | None = None


def get_engine() -> OSINTEngine:
    global _engine
    if _engine is None:
        _engine = OSINTEngine()
    return _engine
