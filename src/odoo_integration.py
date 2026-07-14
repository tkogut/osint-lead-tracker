"""
odoo_integration.py — Integracja z Odoo przez XML-RPC.
Tworzy rekordy crm.lead na podstawie danych z OSINT Engine.
Wspiera architekturę wielofirmową (company_id, user_id, tag_ids) per kampania.
"""

import logging
import xmlrpc.client
from typing import Optional, List

from config import get_settings
from database import get_db_setting_sync

logger = logging.getLogger(__name__)


class OdooClient:
    """Thread-safe klient XML-RPC dla Odoo."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Autoryzacja
    # ------------------------------------------------------------------
    def _authenticate(self) -> int:
        """
        Loguje się do Odoo i zwraca UID użytkownika.
        Pobiera dane logowania dynamicznie z bazy danych (ustawienia globalne).
        """
        odoo_url = get_db_setting_sync("ODOO_URL", self._settings.odoo_url)
        odoo_db = get_db_setting_sync("ODOO_DB", self._settings.odoo_db)
        odoo_user = get_db_setting_sync("ODOO_USER", self._settings.odoo_user)
        odoo_api_key = get_db_setting_sync("ODOO_API_KEY", self._settings.odoo_api_key)

        try:
            common = xmlrpc.client.ServerProxy(
                f"{odoo_url}/xmlrpc/2/common", allow_none=True
            )
            uid = common.authenticate(odoo_db, odoo_user, odoo_api_key, {})
            if not uid:
                raise ValueError(
                    "Odoo authenticate() zwróciło False — sprawdź ODOO_USER/ODOO_API_KEY."
                )
            logger.info("Odoo auth OK → uid=%s db=%s", uid, odoo_db)
            return uid
        except Exception as exc:
            logger.error("Odoo auth FAILED: %s", exc)
            raise

    def _models_proxy(self) -> xmlrpc.client.ServerProxy:
        odoo_url = get_db_setting_sync("ODOO_URL", self._settings.odoo_url)
        return xmlrpc.client.ServerProxy(
            f"{odoo_url}/xmlrpc/2/object", allow_none=True
        )

    # ------------------------------------------------------------------
    # Publiczne API
    # ------------------------------------------------------------------
    def create_lead(
        self,
        lead: dict,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        team_id: Optional[int] = None,
        source_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Tworzy nową szansę sprzedaży w modelu crm.lead.
        Wspiera parametry wielofirmowości (company_id, user_id, tag_ids).
        """
        odoo_db = get_db_setting_sync("ODOO_DB", self._settings.odoo_db)
        odoo_api_key = get_db_setting_sync("ODOO_API_KEY", self._settings.odoo_api_key)

        # --- buduj opis HTML ---
        typ = lead.get("typ") or "brak danych"
        data_pub = lead.get("data") or lead.get("data_pub") or "brak danych"
        lokalizacja = lead.get("lokalizacja") or "brak danych"
        inwestor = lead.get("inwestor") or "brak danych"
        wykonawca = lead.get("wykonawca") or "brak danych"
        zakres = lead.get("zakres") or "brak danych"
        uzasadnienie = lead.get("uzasadnienie") or "brak danych"
        priorytet = lead.get("priorytet") or "brak danych"
        url = lead.get("url") or "#"
        opis_szczeg = lead.get("opis_szczegolowy") or ""

        table_style = "width: 100%; border-collapse: collapse; margin-bottom: 15px;"
        td_label_style = "padding: 6px 10px; font-weight: bold; border-bottom: 1px solid #eeeeee; width: 30%; text-align: left;"
        td_val_style = "padding: 6px 10px; border-bottom: 1px solid #eeeeee; text-align: left;"

        description = f"""<h3>📋 SZCZEGÓŁY ZAPYTANIA OSINT</h3>
<table style="{table_style}">
  <tr>
    <td style="{td_label_style}">Kategoria zamówienia:</td>
    <td style="{td_val_style}">{typ}</td>
  </tr>
  <tr>
    <td style="{td_label_style}">Lokalizacja:</td>
    <td style="{td_val_style}">{lokalizacja}</td>
  </tr>
  <tr>
    <td style="{td_label_style}">Inwestor / Zamawiający:</td>
    <td style="{td_val_style}">{inwestor}</td>
  </tr>
  <tr>
    <td style="{td_label_style}">Wykonawca:</td>
    <td style="{td_val_style}">{wykonawca}</td>
  </tr>
  <tr>
    <td style="{td_label_style}">Termin publikacji:</td>
    <td style="{td_val_style}">{data_pub}</td>
  </tr>
  <tr>
    <td style="{td_label_style}">Priorytet:</td>
    <td style="{td_val_style}"><strong>{priorytet.upper()}</strong></td>
  </tr>
</table>

<h4>🏗️ Zakres związany z wagą samochodową:</h4>
<p>{zakres}</p>

<h4>💡 Uzasadnienie potencjału handlowego:</h4>
<p><em>{uzasadnienie}</em></p>
"""
        if opis_szczeg:
            description += f"""
<h4>📝 Dodatkowe szczegóły:</h4>
<p>{opis_szczeg}</p>
"""

        description += f"""
<hr/>
<p>🔗 <strong>Źródło zamówienia:</strong> <a href="{url}" target="_blank">Otwórz oficjalne ogłoszenie w nowej karcie</a></p>
"""

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
            "type": "lead",
        }

        # Dynamiczne mapowanie Odoo
        if company_id:
            vals["company_id"] = company_id
        if user_id is not None:
            vals["user_id"] = user_id
        if tag_ids:
            # Mapowanie M2M Odoo
            vals["tag_ids"] = [(6, 0, tag_ids)]
        if team_id:
            vals["team_id"] = team_id
        if source_id:
            vals["source_id"] = source_id

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
                odoo_db,
                uid,
                odoo_api_key,
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

    def get_leads_status(self, odoo_ids: List[int]) -> List[dict]:
        """
        Pobiera statusy (active, probability) dla podanych id crm.lead.
        """
        if not odoo_ids:
            return []
        odoo_db = get_db_setting_sync("ODOO_DB", self._settings.odoo_db)
        odoo_api_key = get_db_setting_sync("ODOO_API_KEY", self._settings.odoo_api_key)
        try:
            uid = self._authenticate()
            models = self._models_proxy()
            records = models.execute_kw(
                odoo_db,
                uid,
                odoo_api_key,
                "crm.lead",
                "search_read",
                [[["id", "in", odoo_ids]]],
                {"fields": ["id", "active", "probability"]}
            )
            return records
        except Exception as exc:
            logger.error("Odoo get_leads_status FAILED: %s", exc)
            return []


# Singleton — reused across requests/scheduler runs
_odoo_client: Optional[OdooClient] = None


def get_odoo_client() -> OdooClient:
    global _odoo_client
    if _odoo_client is None:
        _odoo_client = OdooClient()
    return _odoo_client
