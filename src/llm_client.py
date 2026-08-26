"""
llm_client.py — Unified LLM client supporting Google Gemini and OpenRouter API providers.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings
from database import get_db_setting_sync

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_AUTH_URL = "https://openrouter.ai/api/v1/auth/key"

_cached_models: Optional[List[Dict[str, Any]]] = None
_cache_timestamp: float = 0.0
_CACHE_TTL_SECONDS: float = 900.0  # 15 minutes

CURATED_OPENROUTER_MODELS = [
    {"id": "anthropic/claude-3.7-sonnet", "name": "Claude 3.7 Sonnet", "provider": "OpenRouter"},
    {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku", "provider": "OpenRouter"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenRouter"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenRouter"},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "provider": "OpenRouter"},
    {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "provider": "OpenRouter"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "provider": "OpenRouter"},
    {"id": "mistralai/mistral-large-2411", "name": "Mistral Large 2411", "provider": "OpenRouter"},
    {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B", "provider": "OpenRouter"},
    {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash (OpenRouter)", "provider": "OpenRouter"},
]

DEFAULT_GEMINI_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Gemini"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Gemini"},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "Gemini"},
    {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "Gemini"},
    {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Gemini"},
]


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    raw_response: Optional[Any] = None


def is_openrouter_model(model: str) -> bool:
    """Checks if a model string belongs to OpenRouter."""
    if not model:
        return False
    return "/" in model or model.startswith("openrouter/")


async def generate_content_with_llm(
    model: str,
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.1,
    max_output_tokens: int = 2048,
    tools: Optional[list] = None,
    timeout: float = 60.0
) -> LLMResult:
    """
    Unified entry point for LLM generation. Routes to OpenRouter or Google Gemini SDK.
    """
    settings = get_settings()

    if is_openrouter_model(model):
        provider = "OpenRouter"
        clean_model = model[len("openrouter/"):] if model.startswith("openrouter/") else model
        api_key = get_db_setting_sync("OPENROUTER_API_KEY", "")
        if not api_key:
            logger.warning("OPENROUTER_API_KEY is empty when invoking model: %s", clean_model)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/tkogut/osint-lead-tracker",
            "X-Title": "OSINT Lead Tracker",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": clean_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                err_body = resp.text
                logger.error("OpenRouter API error (%d): %s", resp.status_code, err_body)
                raise RuntimeError(f"OpenRouter API error (HTTP {resp.status_code}): {err_body}")

            data = resp.json()
            choices = data.get("choices", [])
            output_text = ""
            if choices and len(choices) > 0:
                msg = choices[0].get("message", {})
                output_text = msg.get("content", "") or ""

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0) or 0
            output_tokens = usage.get("completion_tokens", 0) or 0

            return LLMResult(
                text=output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=clean_model,
                provider=provider,
                raw_response=data
            )
    else:
        provider = "Gemini"
        api_key = get_db_setting_sync("GEMINI_API_KEY", settings.gemini_api_key)
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            config_kwargs["tools"] = tools

        config = types.GenerateContentConfig(**config_kwargs)

        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
        )

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", getattr(response.usage_metadata, "input_token_count", 0)) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", getattr(response.usage_metadata, "output_token_count", 0)) or 0

        text = response.text or ""
        return LLMResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            provider=provider,
            raw_response=response
        )


async def fetch_available_models(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Returns list of model dicts:
    [{"id": model_id, "name": display_name, "provider": "Gemini" | "OpenRouter"}, ...]
    Caches model list in-memory for _CACHE_TTL_SECONDS (15 min).
    """
    global _cached_models, _cache_timestamp

    if not force_refresh and _cached_models is not None:
        if time.time() - _cache_timestamp < _CACHE_TTL_SECONDS:
            return _cached_models

    gemini_models: List[Dict[str, Any]] = []
    openrouter_models: List[Dict[str, Any]] = []
    settings = get_settings()

    # 1. Fetch Gemini models
    gemini_key = get_db_setting_sync("GEMINI_API_KEY", settings.gemini_api_key)
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            import asyncio
            loop = asyncio.get_running_loop()
            models_list = await loop.run_in_executor(None, client.models.list)
            for m in models_list:
                name = m.name or ""
                if "gemini" in name.lower():
                    methods = getattr(m, "supported_generation_methods", None) or getattr(m, "supported_actions", None)
                    if methods and "generateContent" in methods:
                        clean_name = name
                        if clean_name.startswith("models/"):
                            clean_name = clean_name[len("models/"):]
                        display_name = getattr(m, "display_name", None) or clean_name
                        gemini_models.append({
                            "id": clean_name,
                            "name": display_name,
                            "provider": "Gemini"
                        })
        except Exception as e:
            logger.warning("Failed to dynamically fetch Gemini models: %s", e)

    if not gemini_models:
        gemini_models.extend(DEFAULT_GEMINI_MODELS)

    # 2. Fetch OpenRouter models (public endpoint, works with or without key)
    openrouter_key = get_db_setting_sync("OPENROUTER_API_KEY", "")
    try:
        headers = {
            "HTTP-Referer": "https://github.com/tkogut/osint-lead-tracker",
            "X-Title": "OSINT Lead Tracker",
        }
        if openrouter_key:
            headers["Authorization"] = f"Bearer {openrouter_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPENROUTER_MODELS_URL, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                or_models = data.get("data", [])
                for item in or_models:
                    m_id = item.get("id")
                    if not m_id:
                        continue
                    name = item.get("name") or m_id
                    openrouter_models.append({
                        "id": m_id,
                        "name": name,
                        "provider": "OpenRouter"
                    })
    except Exception as e:
        logger.warning("Failed to dynamically fetch OpenRouter models: %s", e)

    if not openrouter_models:
        openrouter_models.extend(CURATED_OPENROUTER_MODELS)
    else:
        openrouter_models.sort(key=lambda x: (x.get("name") or "").lower())

    combined = gemini_models + openrouter_models
    _cached_models = combined
    _cache_timestamp = time.time()

    return combined
