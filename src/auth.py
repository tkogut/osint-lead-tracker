"""
auth.py — Funkcje pomocnicze uwierzytelniania, hashowania haseł i sesji.
Zgodne z wzorcami bezpieczeństwa baseline.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Session


def generate_salt() -> str:
    """Generuje kryptograficznie bezpieczną sól."""
    return secrets.token_hex(16)


def generate_session_token() -> str:
    """Generuje unikalny token sesji."""
    return secrets.token_urlsafe(64)


def hash_password(password: str, salt: str) -> str:
    """Hashuje hasło przy użyciu PBKDF2-SHA256 z podaną solą."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Weryfikuje czy podane hasło zgadza się z hashem w bazie."""
    return hash_password(password, salt) == password_hash


async def create_user_session(session: AsyncSession, user_id: int, ttl_hours: int = 24) -> str:
    """Tworzy i zapisuje nową trwałą sesję w bazie danych."""
    token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    db_session = Session(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    session.add(db_session)
    await session.commit()
    return token


async def validate_session_token(session: AsyncSession, token: str) -> Optional[User]:
    """Weryfikuje token sesji w bazie danych i zwraca powiązanego użytkownika."""
    result = await session.execute(
        select(Session).filter(Session.token == token).limit(1)
    )
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        return None
        
    if db_session.expires_at < datetime.utcnow():
        # Usuwamy przeterminowaną sesję
        await session.delete(db_session)
        await session.commit()
        return None
        
    # Pobieramy użytkownika
    user_result = await session.execute(
        select(User).filter(User.id == db_session.user_id).limit(1)
    )
    return user_result.scalar_one_or_none()
