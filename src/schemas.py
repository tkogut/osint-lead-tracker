"""
schemas.py — Schematy walidacji Pydantic dla interfejsów API Lead Dashboard.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Żądanie logowania."""
    username: str
    password: str


class AccountCreate(BaseModel):
    """Dane potrzebne do utworzenia nowego konta/kampanii."""
    name: str = Field(..., min_length=1, max_length=255)
    target_cpvs: List[str] = []
    target_keywords: List[str] = []
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


class AccountResponse(BaseModel):
    """Model odpowiedzi profilu konta/kampanii."""
    id: int
    name: str
    target_cpvs: List[str]
    target_keywords: List[str]
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
    raw_text: str
    prompt: str
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096


class SettingUpdate(BaseModel):
    """Zaktualizowanie pojedynczego ustawienia globalnego."""
    key: str
    value: str
