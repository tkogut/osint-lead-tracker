"""
schemas.py — Schematy walidacji Pydantic dla interfejsów API Lead Dashboard.
"""

from typing import List, Optional, Text
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    """Żądanie logowania."""
    username: str
    password: str


class AccountCreate(BaseModel):
    """Dane potrzebne do utworzenia nowego konta/kampanii."""
    name: str = Field(..., min_length=1, max_length=255)
    target_cpvs: List[str] = []
    target_keywords: List[str] = []
    enabled_sources: List[str] = Field(default_factory=lambda: ["BZP", "Google", "GUNB"])
    custom_prompt: Optional[str] = None
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = Field(0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(4096, gt=0)
    
    # Odoo Multi-company i mapowanie
    odoo_company_id: Optional[int] = None
    odoo_user_id: Optional[int] = None
    odoo_tag_ids: List[int] = []
    
    odoo_team_id: Optional[int] = None
    odoo_source_id: Optional[int] = None
    is_active: bool = True

    @field_validator("enabled_sources")
    @classmethod
    def validate_enabled_sources(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("Musi być wybrane co najmniej jedno źródło wyszukiwania.")
        return v


class AccountResponse(BaseModel):
    """Model odpowiedzi profilu konta/kampanii."""
    id: int
    name: str
    target_cpvs: List[str]
    target_keywords: List[str]
    enabled_sources: List[str]
    custom_prompt: Optional[str]
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    odoo_company_id: Optional[int]
    odoo_user_id: Optional[int]
    odoo_tag_ids: List[int]
    odoo_team_id: Optional[int]
    odoo_source_id: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


class SandboxRequest(BaseModel):
    """Żądanie uruchomienia testu w piaskownicy (Sandbox)."""
    raw_text: Optional[str] = None
    url: Optional[str] = None
    prompt: str
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096


class SandboxFetchUrlRequest(BaseModel):
    """Żądanie pobrania i czyszczenia URL do testu."""
    url: str


class SettingUpdate(BaseModel):
    """Zaktualizowanie pojedynczego ustawienia globalnego."""
    key: str
    value: str


class ChangePasswordRequest(BaseModel):
    """Ządanie zmiany hasła administratora."""
    old_password: str
    new_password: str


class LeadResponse(BaseModel):
    """Model odpowiedzi leada z polami Phase 5."""
    id: int
    url: Optional[str]
    tytul: Optional[str]
    typ: Optional[str]
    lokalizacja: Optional[str]
    inwestor: Optional[str]
    wykonawca: Optional[str]
    zakres: Optional[Text]
    uzasadnienie: Optional[Text]
    priorytet: Optional[str]
    data_pub: Optional[str]
    odoo_id: Optional[int]
    status: str = 'new'
    prompt_version_id: Optional[int]
    last_synced_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class LeadSyncResponse(BaseModel):
    """Odpowiedź operacji synchronizacji leadów z Odoo."""
    synced: int
    errors: int
