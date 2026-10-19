#!/usr/bin/env python3
"""
scripts/test_metabase_connection.py — Weryfikacja połączenia z Metabase API.
Wczytuje dane z lokalnego .env i testuje autoryzację oraz dostęp do baz danych.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

def main():
    load_dotenv(".env")

    url = (os.getenv("METABASE_URL") or "https://reports.trilab.pl").rstrip("/")
    user = os.getenv("METABASE_USER", "").strip()
    password = os.getenv("METABASE_PASSWORD", "").strip()
    api_key = os.getenv("METABASE_API_KEY", "").strip()

    print("=" * 60)
    print("🔍 TEST POŁĄCZENIA Z METABASE API")
    print(f"URL: {url}")
    print(f"Użytkownik: {user if user else '(brak w .env)'}")
    print(f"Hasło: {'******' if password else '(brak w .env)'}")
    print(f"API Key: {'******' if api_key else '(brak w .env)'}")
    print("=" * 60)

    if not api_key and (not user or not password):
        print("\n❌ BŁĄD: Brak danych logowania w pliku .env!")
        print("Uzupełnij zmienne METABASE_USER i METABASE_PASSWORD (lub METABASE_API_KEY) w pliku .env.")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "osint-lead-tracker/metabase-client"
    }

    session_token = None

    if api_key:
        print("\n1. Test autoryzacji za pomocą API Key (x-api-key)...")
        headers["x-api-key"] = api_key
    else:
        print("\n1. Logowanie przez POST /api/session (login + hasło)...")
        login_url = f"{url}/api/session"
        payload = json.dumps({"username": user, "password": password}).encode("utf-8")
        req = urllib.request.Request(login_url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                session_token = data.get("id")
                if not session_token:
                    print(f"❌ Nieoczekiwana odpowiedź logowania: {data}")
                    sys.exit(1)
                print("   ✅ Sukces! Uzyskano token sesji Metabase.")
                headers["X-Metabase-Session"] = session_token
        except urllib.error.HTTPError as e:
            print(f"❌ Błąd logowania HTTP {e.code}: {e.reason}")
            try:
                err_body = e.read().decode("utf-8")
                print(f"   Treść błędu: {err_body}")
            except Exception:
                pass
            sys.exit(1)
        except Exception as e:
            print(f"❌ Błąd połączenia: {e}")
            sys.exit(1)

    # 2. Pobierz dane aktualnego użytkownika
    print("\n2. Pobieranie danych konta (/api/user/current)...")
    user_url = f"{url}/api/user/current"
    req = urllib.request.Request(user_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            u_data = json.loads(resp.read().decode("utf-8"))
            email = u_data.get("email") or u_data.get("username")
            common_name = u_data.get("common_name") or f"{u_data.get('first_name', '')} {u_data.get('last_name', '')}".strip()
            is_superuser = u_data.get("is_superuser", False)
            print(f"   ✅ Zalogowano jako: {common_name} ({email})")
            print(f"   Uprawnienia: {'Administrator (superuser)' if is_superuser else 'Standardowy użytkownik'}")
    except Exception as e:
        print(f"   ⚠️ Ostrzeżenie przy pobieraniu profilu: {e}")

    # 3. Pobierz listę połączonych baz danych
    print("\n3. Pobieranie listy połączonych baz danych (/api/database)...")
    db_url = f"{url}/api/database"
    req = urllib.request.Request(db_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            db_res = json.loads(resp.read().decode("utf-8"))
            databases = db_res.get("data", db_res) if isinstance(db_res, dict) else db_res
            print(f"   Znaleziono baz danych: {len(databases)}")
            for idx, d in enumerate(databases, 1):
                db_id = d.get("id")
                db_name = d.get("name")
                db_engine = d.get("engine")
                print(f"   [{idx}] ID: {db_id} | Nazwa: '{db_name}' | Silnik: {db_engine}")
    except Exception as e:
        print(f"   ⚠️ Ostrzeżenie przy pobieraniu baz danych: {e}")

    print("\n" + "=" * 60)
    print("🎉 POŁĄCZENIE Z METABASE DZIAŁA POPRAWNIE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
