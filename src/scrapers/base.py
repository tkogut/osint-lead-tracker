"""
base.py — Abstrakcyjna klasa bazowa dla dedykowanych wtyczek skraperów oraz DOMSanitizer.
"""

import abc
import logging
import re
from typing import List, Dict, Any, Optional

import trafilatura

logger = logging.getLogger(__name__)


class DOMSanitizer:
    """
    Ekstrahuje czysty tekst z surowego kodu HTML, wycinając szum DOM (nawigacje, reklamy, stopki),
    co pozwala zaoszczędzić tokeny i zapobiega halucynacjom LLM.
    """

    LOGINTRADE_BOILERPLATE_PATTERNS = [
        r"Enquiry\s+is\s+out\s+of\s+date\.?",
        r"Time\s+to\s+make\s+an\s+offer\s+is\s+up(?:\s*\.\.\.|\s*\.)?",
        r"The\s+Purchasing\s+Platform\s+Terms\s+of\s+Use\s+are\s+available\s+in\s+the\s+registration\s+panel\.?",
        r"Registering\s+in\s+our\s+company\s+suppliers\s+base,?\s+receiving\s+enquiries\s+and\s+making\s+sales\s+offers\s+are\s+free\s+of\s+charge\.?",
        r"To\s+browse\s+enquiries\s+from\s+a\s+given\s+company,?\s+you\s+must\s+be\s+registered\s+in\s+their\s+suppliers\s+database\.?",
    ]

    @staticmethod
    def clean(html_content: str, max_chars: int = 6000) -> str:
        """
        Wyciąga czysty tekst za pomocą Trafilatura, a w przypadku braku wyniku stosuje czyszczenie regex.
        Wykonuje również czyszczenie stopek systemowych Logintrade.
        """
        if not html_content or not html_content.strip():
            return ""

        extracted = trafilatura.extract(
            html_content,
            include_links=True,
            include_tables=True,
            no_fallback=False
        )

        if not extracted:
            # Fallback regex cleaning
            text = re.sub(
                r"<(script|style|nav|footer|header|aside|iframe)[^>]*>.*?</\1>",
                "",
                html_content,
                flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(r"<[^>]+>", " ", text)
            text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            extracted = " ".join(text.split())

        # Czyszczenie stopek systemowych Logintrade
        for pattern in DOMSanitizer.LOGINTRADE_BOILERPLATE_PATTERNS:
            extracted = re.sub(pattern, "", extracted, flags=re.IGNORECASE)

        extracted = " ".join(extracted.split())

        return extracted[:max_chars].strip()


class BaseScraper(abc.ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich dedykowanych skraperów (wtyczek źródeł).
    """

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    @abc.abstractmethod
    async def fetch_leads(self, account: Any, start_date: str, today_date: str) -> List[Dict[str, Any]]:
        """
        Pobiera i analizuje ogłoszenia dla podanej kampanii (Account).
        Zwraca listę słowników z surowymi danymi ogłoszeń (url, tytul, raw_text, data itp.).
        """
        pass
