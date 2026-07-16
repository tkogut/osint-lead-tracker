"""
models.py — Definicje modeli SQLAlchemy dla osint-lead-tracker.
Zgodne z AGENTS-OS v5.0 i architekturą bazy danych SQLite.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """Konta użytkowników / administratorów panelu Dashboard."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="admin")

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Trwałe sesje użytkowników w bazie danych."""
    __tablename__ = "sessions"

    token = Column(String(256), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")


class Account(Base):
    """Konta (kampanie/produkty) obsługiwane przez system (Multi-tenancy)."""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    
    # Parametry wyszukiwania (przechowywane jako JSON-serialized strings)
    target_cpvs = Column(Text, nullable=False, default="[]")
    target_keywords = Column(Text, nullable=False, default="[]")
    
    # Konfiguracja LLM per konto
    custom_prompt = Column(Text, nullable=True)
    llm_model = Column(String(100), nullable=False, default="gemini-2.5-flash")
    llm_temperature = Column(Float, nullable=False, default=0.1)
    llm_max_tokens = Column(Integer, nullable=False, default=4096)
    
    # Odoo Multicompany & Salesperson mapping (company_id, user_id, tag_ids)
    odoo_company_id = Column(Integer, nullable=True)  # Company ID w Odoo (Multicompany)
    odoo_user_id = Column(Integer, nullable=True)     # ID handlowca w Odoo (optional)
    odoo_tag_ids = Column(Text, nullable=False, default="[]")  # Tag IDs w Odoo (JSON list)
    
    # Odoo Team & Source mapping
    odoo_team_id = Column(Integer, nullable=True)
    odoo_source_id = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    logs = relationship("ResearchLog", back_populates="account", cascade="all, delete-orphan")
    prompt_versions = relationship("PromptVersion", back_populates="account", cascade="all, delete-orphan")
    snapshots = relationship("RunPerformanceSnapshot", back_populates="account", cascade="all, delete-orphan")


class ResearchLog(Base):
    """Rejestr akcji researchu zawierający metadane i lekki twardy dowód (Hash)."""
    __tablename__ = "research_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    source = Column(String(50), nullable=False)  # BZP, GUNB, Google
    query_params = Column(Text, nullable=True)   # Parametry zapytania (JSON)
    
    raw_response_hash = Column(String(64), nullable=False)  # Matematyczny dowód (SHA-256 hash surowej odpowiedzi)
    response_status_code = Column(Integer, nullable=False)
    
    leads_found_count = Column(Integer, nullable=False, default=0)
    leads_created_count = Column(Integer, nullable=False, default=0)
    log_text = Column(Text, nullable=True)

    # Phase 6: Grounding metadata and token economy
    grounding_chunks_count = Column(Integer, nullable=True, default=0)
    grounding_queries_count = Column(Integer, nullable=True, default=0)
    input_tokens = Column(Integer, nullable=True, default=0)
    output_tokens = Column(Integer, nullable=True, default=0)

    account = relationship("Account", back_populates="logs")


class Setting(Base):
    """Globalna konfiguracja (zmienne środowiskowe, klucze API) przechowywana w bazie."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)


class Lead(Base):
    """Model leadów - kompatybilny wstecznie z dotychczasową tabelą leads w SQLite."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), unique=True, nullable=False)
    tytul = Column(String(500), nullable=False)
    typ = Column(String(100))
    lokalizacja = Column(String(255))
    inwestor = Column(String(255))
    wykonawca = Column(String(255))
    zakres = Column(Text)
    uzasadnienie = Column(Text)
    priorytet = Column(String(50))
    data_pub = Column(String(50))
    odoo_id = Column(Integer, nullable=True)
    created_at = Column(String(100), nullable=False, default=lambda: datetime.utcnow().isoformat())
    # Phase 5: status, prompt versioning, sync
    status = Column(String(50), nullable=False, default='new')
    prompt_version_id = Column(Integer, ForeignKey('prompt_versions.id', ondelete='SET NULL'), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    pending_approval = Column(Boolean, nullable=False, default=False)


class PromptVersion(Base):
    """Wersjonowanie promptów systemowych per kampania."""
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    account = relationship("Account", back_populates="prompt_versions")


class RunPerformanceSnapshot(Base):
    """Snapshot wydajności per przebieg (źródło + konto) — metryki Grounding i tokenów."""
    __tablename__ = "run_performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)          # BZP / Google / GUNB
    run_date = Column(String(10), nullable=False)        # YYYY-MM-DD
    leads_generated = Column(Integer, nullable=False, default=0)
    grounding_chunks_count = Column(Integer, nullable=False, default=0)
    grounding_queries_count = Column(Integer, nullable=False, default=0)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    api_errors = Column(Integer, nullable=False, default=0)
    circuit_breaker_triggered = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    account = relationship("Account", back_populates="snapshots")
