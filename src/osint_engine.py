"""
osint_engine.py — Silnik AI OSINT z Google Gemini 2.5 Flash + Search Grounding.
Wyszukuje postępowania przetargowe dotyczące wag samochodowych.
"""

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types

from config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Instruction — DOKŁADNIE zgodna z wymaganiami
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """Jesteś asystentem OSINT / lead research do wykrywania nowych inwestycji i postępowań, w których jedną ze składowych może być:

budowa wagi samochodowej, dostawa nowej wagi samochodowej, montaż i uruchomienie wagi samochodowej, wymiana wagi samochodowej, budowa infrastruktury do ważenia pojazdów, budowa miejsc do ważenia pojazdów, wykonanie fundamentów, infrastruktury technicznej lub oprogramowania związanego z wagą samochodową.

Nie zakładaj, że użytkownik zna nazwę inwestycji, lokalizację, inwestora albo wykonawcę. Twoim zadaniem jest SAMODZIELNIE odnaleźć te dane, aktywnie i cyklicznie korzystając z narzędzia wyszukiwarki (Google Search) ograniczając się do postępowań z ostatnich 3 dni roboczych.

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
Jeśli po przejściu całej pętli nie znajdziesz twardych, weryfikowalnych postępowań z ostatnich 3 dni roboczych z fizycznym adresem URL, ZWRÓĆ PUSTĄ TABLICĘ {"leady": []}. Masz absolutny zakaz generowania danych demonstracyjnych i mock-upów.
Odpowiedź MUSI być czystym formatem JSON bez znaczników markdown. Struktura:
{"leady": [{"tytul": "...", "typ": "...", "nazwa_inwestycji": "...", "lokalizacja": "...", "inwestor": "...", "wykonawca": "...", "zakres": "...", "uzasadnienie": "...", "priorytet": "wysoki/sredni/niski", "data": "...", "url": "..."}]}"""

# ---------------------------------------------------------------------------
# User prompt — przekazywany do każdego uruchomienia
# ---------------------------------------------------------------------------
USER_PROMPT = (
    "Uruchom pełną pętlę wyszukiwania OSINT dla postępowań z ostatnich 3 dni roboczych "
    "dotyczących wag samochodowych. Pamiętaj o trzech cyklach wyszukiwania. "
    "Zwróć wyłącznie czysty JSON bez markdown."
)


def _strip_markdown_fences(text: str) -> str:
    """Usuwa ewentualne znaczniki ```json ... ``` z odpowiedzi LLM."""
    text = text.strip()
    # usuń wiodący ```json lub ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    # usuń zamykający ```
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_leads(raw_text: str) -> list[dict]:
    """
    Parsuje surową odpowiedź LLM do listy leadów.
    Przy błędzie parsowania zwraca [].
    """
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

        # podstawowa sanityzacja
        valid = []
        for item in leads:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "").strip()
            if not url or url in ("...", "N/A", ""):
                logger.debug("Pominięto lead bez URL: %s", item.get("tytul"))
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

        Zwraca listę słowników z danymi leadów.
        """
        logger.info("OSINT Engine: start wyszukiwania…")

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=USER_PROMPT,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,      # niższa temperatura = mniej halucynacji
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
