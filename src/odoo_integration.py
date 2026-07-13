"""
odoo_integration.py — Integracja z Odoo przez XML-RPC.
Tworzy rekordy crm.lead na podstawie danych z OSINT Engine.
"""

import logging
import xmlrpc.client
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)


class OdooClient:
    """Thread-safe klient XML-RPC dla Odoo."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._uid: Optional[int] = None

    # ------------------------------------------------------------------
    # Autoryzacja
    # ------------------------------------------------------------------
    def _authenticate(self) -> int:
        """
        Loguje się do Odoo i zwraca UID użytkownika.
        Wynik jest cache'owany na czas życia instancji.
        """
        if self._uid is not None:
            return self._uid

        s = self._settings
        try:
            common = xmlrpc.client.ServerProxy(
                f"{s.odoo_url}/xmlrpc/2/common", allow_none=True
            )
            uid = common.authenticate(s.odoo_db, s.odoo_user, s.odoo_password, {})
            if not uid:
                raise ValueError(
                    "Odoo authenticate() zwróciło False — sprawdź ODOO_USER/ODOO_PASSWORD."
                )
            self._uid = uid
            logger.info("Odoo auth OK → uid=%s db=%s", uid, s.odoo_db)
            return uid
        except Exception as exc:
            logger.error("Odoo auth FAILED: %s", exc)
            raise

    def _models_proxy(self) -> xmlrpc.client.ServerProxy:
        s = self._settings
        return xmlrpc.client.ServerProxy(
            f"{s.odoo_url}/xmlrpc/2/object", allow_none=True
        )

    # ------------------------------------------------------------------
    # Publiczne API
    # ------------------------------------------------------------------
    def create_lead(self, lead: dict) -> Optional[int]:
        """
        Tworzy nową szansę sprzedaży w modelu crm.lead.

        Oczekiwane klucze w ``lead``:
          tytul, tytul_generowany, lokalizacja, inwestor, wykonawca,
          zakres, uzasadnienie, url, priorytet, data, typ,
          email (opcjonalny), telefon (opcjonalny),
          termin_skladania (opcjonalny, YYYY-MM-DD),
          opis_szczegolowy (opcjonalny)

        Zwraca Odoo record id lub None przy błędzie.
        """
        s = self._settings

        # --- buduj opis ---
        url_part = f"Źródło: {lead.get('url', 'brak')}"
        opis_szczeg = lead.get("opis_szczegolowy") or ""
        lokalizacja = lead.get("lokalizacja") or ""
        inwestor = lead.get("inwestor") or ""
        wykonawca = lead.get("wykonawca") or ""
        zakres = lead.get("zakres") or ""
        uzasadnienie = lead.get("uzasadnienie") or ""
        priorytet = lead.get("priorytet") or ""

        description_parts = [
            url_part,
            f"\n--- Szczegóły ---",
            f"Lokalizacja: {lokalizacja}",
            f"Inwestor/Zamawiający: {inwestor}",
            f"Wykonawca: {wykonawca}",
            f"Zakres (waga): {zakres}",
            f"Uzasadnienie: {uzasadnienie}",
            f"Priorytet: {priorytet}",
        ]
        if opis_szczeg:
            description_parts.append(f"\n{opis_szczeg}")

        description = "\n".join(description_parts)

        # --- nazwa leada ---
        name = (
            lead.get("tytul_generowany")
            or lead.get("tytul")
            or "OSINT Lead – waga samochodowa"
        )

        # --- mapowanie pól Odoo ---
        vals: dict = {
            "name": name,
            "description": description,
            "type": "opportunity",
        }

        if s.odoo_team_id:
            vals["team_id"] = s.odoo_team_id
        if s.odoo_source_id:
            vals["source_id"] = s.odoo_source_id
        if lead.get("email"):
            vals["email_from"] = lead["email"]
        if lead.get("telefon"):
            vals["phone"] = lead["telefon"]
        if lead.get("termin_skladania"):
            vals["date_deadline"] = lead["termin_skladania"]

        # --- priorytet Odoo: 0=normal, 1=low, 2=high, 3=very high ---
        priorytet_map = {"wysoki": "2", "sredni": "1", "niski": "0"}
        odoo_priority = priorytet_map.get(
            str(priorytet).lower().strip(), "1"
        )
        vals["priority"] = odoo_priority

        try:
            uid = self._authenticate()
            models = self._models_proxy()
            record_id: int = models.execute_kw(
                s.odoo_db,
                uid,
                s.odoo_password,
                "crm.lead",
                "create",
                [vals],
            )
            logger.info("Odoo crm.lead created → id=%s name=%s", record_id, name)
            return record_id
        except xmlrpc.client.Fault as fault:
            logger.error(
                "Odoo XML-RPC Fault %s: %s — vals=%s",
                fault.faultCode,
                fault.faultString,
                vals,
            )
            return None
        except Exception as exc:
            logger.error("Odoo create_lead FAILED: %s — vals=%s", exc, vals)
            return None


# Singleton — reused across requests/scheduler runs
_odoo_client: Optional[OdooClient] = None


def get_odoo_client() -> OdooClient:
    global _odoo_client
    if _odoo_client is None:
        _odoo_client = OdooClient()
    return _odoo_client
