# Plan 065: Ponowna Próba Odzyskania URL (Search Recovery) i Ostrzeżenie o Weryfikacji Ręcznej w Odoo

## 1. Kontekst i Nowe Wymagania Użytkownika
* W Planie 064 wprowadzono `url_validator.py`, który odrzucał błędne linki i blokował wysyłkę leada do Odoo.
* **Nowe wytyczne użytkownika:**
  1. **Ponowna próba odszukania (Retry / Search Recovery):** Jeśli link jest pusty, uszkodzony, błędny (np. NXDOMAIN, 404, placeholder), system podejmuje próbę ponownego celowanego wyszukania poprawnego linku w Google (np. po tytule i inwestorze).
  2. **Opcja B (Obsługa w Odoo):** Jeśli ponowna próba również nie przyniesie działającego linku, lead **NIE JEST ODRZUCANY**, lecz **wysyłany do Odoo** z jaskrawym ostrzeżeniem, że link nie działa i wymaga ręcznej weryfikacji handlowca.

---

## 2. Architektura Rozwiązania

### Krok 1: Mechanizm Search Recovery w `src/url_validator.py`
* Nowa funkcja pomocnicza:
  `async def attempt_url_recovery(lead: dict, account: Optional[Any] = None, timeout: float = 8.0) -> Tuple[bool, str, str]`
  * Jeśli pierwotny URL nie przeszedł walidacji:
    * Formułuje celowane zapytanie do wyszukiwarki:
      `q = f"{lead.get('inwestor', '')} {lead.get('tytul', '')} przetarg zapytanie ofertowe"`
    * Wywołuje `gemini-2.5-flash` z `tools=[types.Tool(google_search=types.GoogleSearch())]`:
      *"Odszukaj oficjalny, działający publiczny adres URL ogłoszenia lub zapytania ofertowego dla: {q}. Zwróć wyłącznie jeden bezpośredni URL w formacie JSON: {\"url\": \"...\"}"*
    * Pobrany adres przepuszcza przez `validate_and_resolve_url`.
    * Jeśli nowy adres jest poprawny (`is_valid == True`) → zwraca `(True, recovered_url, "Odzyskano przez ponowne wyszukiwanie")`.
    * Jeśli nadal brak poprawnego URL → zwraca `(False, original_url, reason)`.

### Krok 2: Integracja w `src/main.py` (`run_osint_pipeline`)
* Przed zapisem i eksportem leada:
  1. `is_valid, resolved_url, reason = await validate_and_resolve_url(lead_url)`
  2. Jeśli `not is_valid`:
     * Log: `"[URL Validator] Błędny URL (%s). Uruchamianie ponownej próby wyszukiwania (Search Recovery)..." % reason`
     * `is_valid, resolved_url, reason = await attempt_url_recovery(lead, account=account)`
  3. Jeśli po retry URL jest poprawny:
     * `lead["url"] = resolved_url`
     * `lead["url_status"] = "valid"`
  4. Jeśli po retry URL NADAL nie działa:
     * `lead["url"] = resolved_url`
     * `lead["url_status"] = "invalid"`
     * `lead["url_error"] = reason`
     * Uzupełnienie `uzasadnienie` o tag `[⚠️ LINK WYMAGA WERYFIKACJI RĘCZNEJ: {reason}]`.
  5. **Wysyłka do Odoo:**
     * Lead **JEST wysyłany do Odoo** zarówno gdy URL jest poprawny, jak i gdy wymaga weryfikacji ręcznej.
     * Parametr `url_status="invalid"` oraz `url_error=reason` jest przekazywany do `odoo.create_lead`.

### Krok 3: Ostrzeżenie i formatowanie w Odoo (`src/odoo_integration.py`)
* W `create_lead(..., url_status: str = "valid", url_error: str = "")`:
  * Jeśli `url_status == "invalid"`:
    * Do tytułu leada w Odoo (`name`) dodawany jest prefiks:
      `"[⚠️ WERYFIKACJA LINKU] {name}"`
    * Na samej górze opisu HTML (`description`) wstrzykiwany jest jaskrawy, profesjonalny baner ostrzegawczy:
      ```html
      <div style="background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 12px; margin-bottom: 15px; border-radius: 4px; font-family: sans-serif;">
        <h4 style="margin: 0 0 8px 0; color: #856404;">⚠️ UWAGA: Link źródłowy wymaga weryfikacji ręcznej!</h4>
        <p style="margin: 0 0 6px 0;">Automatyczny weryfikator linków wykrył problem z adresem URL: <strong>{url_error}</strong></p>
        <p style="margin: 0 0 6px 0;">Zarejestrowany link: <code>{url}</code></p>
        <p style="margin: 0;"><strong>Zalecenie dla handlowca:</strong> Wyszukaj postępowanie bezpośrednio na platformie zamawiającego (<strong>{inwestor}</strong>).</p>
      </div>
      ```
    * Pod tabelą w sekcji źródła:
      `🔗 <strong>Źródło zamówienia:</strong> <a href="{url}" target="_blank">{url}</a> <span style="color: #dc3545; font-weight: bold;">(⚠️ Link może być nieaktywny — weryfikacja ręczna)</span>`

### Krok 4: Testy jednostkowe w `tests/test_url_recovery_and_odoo.py`
* Test retry recovery (mock pomyślnego ponownego odszukania URL).
* Test sytuacji, gdy ponowna próba nie odnajdzie linku -> oznaczenie `url_status = "invalid"`.
* Test generowania banera ostrzegawczego HTML w `OdooClient.create_lead`.
* Sprawdzenie pełnego zestawu testów `pytest`.

---

## 3. Kryteria Akceptacji
1. Błędny URL uruchamia automatyczną próbę ponownego wyszukania w Google Search.
2. Przy braku sukcesu lead trafia do Odoo z prefiksem `[⚠️ WERYFIKACJA LINKU]` oraz czytelnym banerem ostrzegawczym w opisie.
3. Wszystkie testy jednostkowe przechodzą (100% PASS).
4. Dual Handshake Buildera i Auditora zarejestrowany w `.agents/swarm/`.
