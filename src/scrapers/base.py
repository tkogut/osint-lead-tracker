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

    @staticmethod
    def clean(html_content: str, max_chars: int = 6000) -> str:
        """
        Wyciąga czysty tekst za pomocą Trafilatura, a w przypadku braku wyniku stosuje czyszczenie regex.
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
