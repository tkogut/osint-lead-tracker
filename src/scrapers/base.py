"""
base.py — Abstrakcyjna klasa bazowa dla dedykowanych wtyczek skraperów oraz DOMSanitizer.
"""

import abc
import logging
import re
from typing import List, Dict, Any, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False

import trafilatura

logger = logging.getLogger(__name__)


class DOMSanitizer:
    """
    Ekstrahuje czysty tekst z surowego kodu HTML, wycinając szum DOM (nawigacje, reklamy, stopki),
    co pozwala zaoszczędzić tokeny i zapobiega halucynacjom LLM.
    """

    DECOMPOSITION_PATTERN = re.compile(r"cookie|consent|rodo|privacy|wadium|modal|banner", re.I)

    LOGINTRADE_BOILERPLATE_PATTERNS = [
        r"Enquiry\s+is\s+out\s+of\s+date\.?",
        r"Time\s+to\s+make\s+an\s+offer\s+is\s+up(?:\s*\.\.\.|\s*\.)?",
        r"The\s+Purchasing\s+Platform\s+Terms\s+of\s+Use\s+are\s+available\s+in\s+the\s+registration\s+panel\.?",
        r"Registering\s+in\s+our\s+company\s+suppliers\s+base,?\s+receiving\s+enquiries\s+and\s+making\s+sales\s+offers\s+are\s+free\s+of\s+charge\.?",
        r"To\s+browse\s+enquiries\s+from\s+a\s+given\s+company,?\s+you\s+must\s+be\s+registered\s+in\s+their\s+suppliers\s+database\.?",
    ]

    COOKIE_AND_GDPR_BOILERPLATE_PATTERNS = [
        # Cookie consent & GDPR privacy banners (PL & EN)
        r"(?:Ta\s+strona|Serwis|Wykorzystujemy|Używamy)\s+(?:korzysta\s+z|używa)\s+plików\s+cookie[s]?.*?(?:zgadzam|akceptuj|polityk[aę]\s+prywatności|ustawienia|dowiedz\s+się\s+więcej|\.|$)",
        r"(?:Pliki\s+cookie[s]?|Cookies)\s+i\s+dane\s+osobowe.*?(?:wyrażam\s+zgodę|zgadzam|akceptuj|\.|$)",
        r"We\s+use\s+cookies\s+to\s+.*?(?:accept|settings|privacy\s+policy|\.|$)",
        r"Informacj[ae]\s+o\s+ochronie\s+danych\s+osobowych\s+\(RODO\).*?(?:zgadzam|akceptuję|wyrażam|\.|$)",
        r"Administratorem\s+(?:Twoich|Państwa|danych)\s+danych\s+osobowych\s+jest.*?(?:RODO|cookies?|polityc[ze]\s+prywatności|\.|$)",
        # GDPR Analytics & Marketing tags (Google Analytics, Meta Pixel, Clarity, LinkedIn Insight Tag)
        r"(?:Google\s+Analytics|Meta\s+Pixel|Microsoft\s+Clarity|Clarity|LinkedIn\s+Insight\s+Tag).*?(?:pliki\s+cookie|dane\s+osobowe|zgoda|polityk[aę]\s+prywatności|śledzen|analityk|\.|$)",
        r"(?:Analityczne|Marketingowe)\s+pliki\s+cookie.*?(?:Google\s+Analytics|Meta\s+Pixel|Clarity|LinkedIn|\.|$)",
    ]

    AD_WIDGET_BOILERPLATE_PATTERNS = [
        # Ad widgets ("Wadium w 2 minuty", "Bid bond in 2 minutes")
        r"Wadium\s+w\s+2\s+minuty.*?(?:kup|zrealizuj|sprawdź|\.|$)",
        r"Bid\s+bond\s+in\s+2\s+minutes.*?(?:check|buy|get|\.|$)",
    ]

    @staticmethod
    def clean(html_content: str, max_chars: int = 6000) -> str:
        """
        Wyciąga czysty tekst za pomocą Trafilatura po uprzednim wyczyszczeniu tagów DOM w BS4,
        a w przypadku braku wyniku stosuje czyszczenie regex.
        Wykonuje również czyszczenie stopek systemowych Logintrade, banerów cookie/RODO i reklam.
        """
        if not html_content or not html_content.strip():
            return ""

        cleaned_html = html_content

        # Pre-cleaning BS4: dekompozycja tagów o class/id/test-id pasujących do wzorca
        if HAS_BS4:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                for tag in list(soup.find_all(True)):
                    if getattr(tag, "decomposed", False):
                        continue
                    matched = False
                    for attr in ("class", "id", "test-id", "data-test-id"):
                        val = tag.get(attr)
                        if val:
                            val_str = " ".join(val) if isinstance(val, list) else str(val)
                            if DOMSanitizer.DECOMPOSITION_PATTERN.search(val_str):
                                matched = True
                                break
                    if matched:
                        tag.decompose()
                cleaned_html = str(soup)
            except Exception as bs_err:
                logger.warning(f"BS4 pre-cleaning failed: {bs_err}")

        extracted = trafilatura.extract(
            cleaned_html,
            include_links=True,
            include_tables=True,
            no_fallback=False
        )

        if not extracted:
            # Fallback regex cleaning
            text = re.sub(
                r"<(script|style|nav|footer|header|aside|iframe)[^>]*>.*?</\1>",
                "",
                cleaned_html,
                flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(r"<[^>]+>", " ", text)
            text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            extracted = " ".join(text.split())

        # Czyszczenie stopek i szumu DOM (Logintrade, Cookie, RODO, Analityka, Reklamy)
        all_patterns = (
            DOMSanitizer.LOGINTRADE_BOILERPLATE_PATTERNS
            + DOMSanitizer.COOKIE_AND_GDPR_BOILERPLATE_PATTERNS
            + DOMSanitizer.AD_WIDGET_BOILERPLATE_PATTERNS
        )
        for pattern in all_patterns:
            extracted = re.sub(pattern, "", extracted, flags=re.IGNORECASE | re.DOTALL)

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
