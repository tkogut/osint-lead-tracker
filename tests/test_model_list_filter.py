"""tests/test_model_list_filter.py — filtr listy modeli Gemini (wycofane / stare / nietekstowe)."""

import pytest

from src.llm_client import is_usable_gemini_model


@pytest.mark.parametrize("model_id", [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
])
def test_current_text_models_are_kept(model_id):
    assert is_usable_gemini_model(model_id)


@pytest.mark.parametrize("model_id", [
    "gemini-2.5-flash-lite",        # 404: no longer available to new users
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-3.5-flash-image",
    "gemini-2.5-flash-preview-tts",
    "gemini-embedding-001",
    "gemma-3-27b-it",
    "",
])
def test_retired_old_or_non_text_models_are_dropped(model_id):
    assert not is_usable_gemini_model(model_id)
