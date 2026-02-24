"""
LLM client interface: single place to choose and configure the LLM backend.

Set LLM_PROVIDER to one of: gemini | openai | bedrock | ollama | deepseek
If unset, provider is auto-detected from API keys (Gemini > OpenAI > DeepSeek > Ollama).

Environment variables per provider:
- gemini: GOOGLE_API_KEY or GEMINI_API_KEY, optional GEMINI_MODEL
- openai: OPENAI_API_KEY, optional OPENAI_MODEL
- bedrock: AWS credentials, optional BEDROCK_MODEL
- ollama: optional OLLAMA_BASE_URL, OLLAMA_MODEL
- deepseek: DEEPSEEK_API_KEY, optional DEEPSEEK_MODEL (default: deepseek-chat)
"""

from __future__ import annotations

import os
from typing import Any

# Load .env so API keys are available
import config  # noqa: F401

# Lazy model imports to avoid requiring all backends
_GoogleModel: Any = None
_OpenAIModel: Any = None
_OllamaModel: Any = None
_BedrockModel: Any = None


def _get_google_model():
    global _GoogleModel
    if _GoogleModel is None:
        try:
            from pydantic_ai.models.google import GoogleModel as M
            _GoogleModel = M
        except ImportError:
            try:
                from pydantic_ai.models.gemini import GeminiModel as M
                _GoogleModel = M
            except ImportError:
                pass
    return _GoogleModel


def _get_openai_model():
    global _OpenAIModel
    if _OpenAIModel is None:
        try:
            from pydantic_ai.models.openai import OpenAIModel as M
            _OpenAIModel = M
        except ImportError:
            pass
    return _OpenAIModel


def _get_ollama_model():
    global _OllamaModel
    if _OllamaModel is None:
        try:
            from pydantic_ai.models.ollama import OllamaModel as M
            _OllamaModel = M
        except ImportError:
            try:
                from pydantic_ai.models import OllamaModel as M
                _OllamaModel = M
            except ImportError:
                pass
    return _OllamaModel


def _get_bedrock_model():
    global _BedrockModel
    if _BedrockModel is None:
        try:
            from pydantic_ai.models.bedrock import BedrockConverseModel as M
            _BedrockModel = M
        except ImportError:
            pass
    return _BedrockModel


def _create_gemini_model():
    GoogleModel = _get_google_model()
    if not GoogleModel:
        raise ImportError("Gemini support not installed. pip install pydantic-ai[google]")
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Set GOOGLE_API_KEY or GEMINI_API_KEY for Gemini.")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    models_to_try = [model_name, "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
    last_error = None
    for name in models_to_try:
        if not name:
            continue
        try:
            return GoogleModel(name, api_key=key)
        except Exception as e:
            last_error = e
    raise ValueError(f"Could not initialize Gemini. Last error: {last_error}") from last_error


def _create_openai_model():
    OpenAIModel = _get_openai_model()
    if not OpenAIModel:
        raise ImportError("OpenAI support not installed. pip install pydantic-ai[openai]")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY for OpenAI.")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAIModel(model_name, api_key=key)


def _create_ollama_model():
    """Create Ollama model: use native OllamaModel if available, else OpenAI-compatible API."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    base_v1 = f"{base}/v1"
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")

    # 1) Prefer pydantic-ai's native Ollama model
    OllamaModel = _get_ollama_model()
    if OllamaModel:
        return OllamaModel(model_name, base_url=base)

    # 2) Fallback: Ollama exposes OpenAI-compatible API at http://localhost:11434/v1
    try:
        # Try passing base_url (older pydantic-ai OpenAIModel may support it)
        OpenAIModel = _get_openai_model()
        if OpenAIModel:
            return OpenAIModel(model_name, api_key="ollama", base_url=base_v1)
    except TypeError:
        pass

    try:
        # Newer pydantic-ai: use OpenAIChatModel + OpenAIProvider with custom client
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        async_client = AsyncOpenAI(base_url=base_v1, api_key="ollama")
        provider = OpenAIProvider(openai_client=async_client)
        return OpenAIChatModel(model_name, provider=provider)
    except (ImportError, TypeError, AttributeError):
        pass

    raise ImportError(
        "Ollama support requires either: (1) pydantic-ai with Ollama model, or "
        "(2) pydantic-ai[openai] with openai package for Ollama's OpenAI-compatible API. "
        "Install: pip install 'pydantic-ai[openai]' openai"
    )


def _create_bedrock_model():
    BedrockModel = _get_bedrock_model()
    if not BedrockModel:
        raise ImportError("Bedrock support not installed. pip install pydantic-ai[bedrock]")
    model_id = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    return BedrockModel(model_id)


def _create_deepseek_model():
    """DeepSeek uses an OpenAI-compatible API at https://api.deepseek.com."""
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("Set DEEPSEEK_API_KEY for DeepSeek. Get one at https://platform.deepseek.com")
    base = "https://api.deepseek.com"
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    OpenAIModel = _get_openai_model()
    if OpenAIModel:
        try:
            return OpenAIModel(model_name, api_key=key, base_url=base)
        except TypeError:
            pass

    try:
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        async_client = AsyncOpenAI(base_url=base, api_key=key)
        provider = OpenAIProvider(openai_client=async_client)
        return OpenAIChatModel(model_name, provider=provider)
    except (ImportError, TypeError, AttributeError) as e:
        raise ImportError(
            "DeepSeek uses the OpenAI-compatible API. Install: pip install 'pydantic-ai[openai]' openai"
        ) from e


def get_llm_model():
    """
    Return the configured LLM model for workers/trainer (structured workout generation).
    Use LLM_PROVIDER=gemini|openai|bedrock|ollama|deepseek to force a provider; otherwise auto-detect.
    """
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    if provider == "gemini":
        return _create_gemini_model()
    if provider == "openai":
        return _create_openai_model()
    if provider == "bedrock":
        return _create_bedrock_model()
    if provider == "ollama":
        return _create_ollama_model()
    if provider == "deepseek":
        return _create_deepseek_model()

    # Auto-detect from API keys: Gemini > OpenAI > DeepSeek > Ollama
    if (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")) and _get_google_model():
        return _create_gemini_model()
    if os.getenv("OPENAI_API_KEY") and _get_openai_model():
        return _create_openai_model()
    if os.getenv("DEEPSEEK_API_KEY") and _get_openai_model():
        return _create_deepseek_model()
    if _get_ollama_model():
        return _create_ollama_model()

    raise ValueError(
        "No LLM configured. Set LLM_PROVIDER (gemini|openai|bedrock|ollama|deepseek) and the corresponding API keys."
    )


def get_supervisor_model():
    """
    Return the configured LLM model for the supervisor (routing and safety).
    Uses the same LLM_PROVIDER and fallbacks as get_llm_model().
    """
    return get_llm_model()
