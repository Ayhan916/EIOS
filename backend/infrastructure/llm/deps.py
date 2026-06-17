"""
LLM provider factory and FastAPI dependency.

Provider is selected from config (LLM_PROVIDER env var).
Adding a new provider requires only: implementing LLMProvider Protocol + adding a branch here.
"""

import structlog

from application.ports.llm import LLMProvider
from shared.config import settings

logger = structlog.get_logger(__name__)

_provider: LLMProvider | None = None


def init_llm_provider() -> LLMProvider:
    """Initialise and cache the configured LLM provider singleton."""
    global _provider
    if _provider is not None:
        return _provider

    name = settings.llm_provider.lower()

    if name == "anthropic":
        from infrastructure.llm.anthropic_provider import AnthropicLLMProvider

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _provider = AnthropicLLMProvider(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
        )

    elif name == "openai":
        from infrastructure.llm.openai_provider import OpenAILLMProvider

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _provider = OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{name}'. "
            "Supported values: anthropic, openai. "
            "To add a new provider, implement LLMProvider in infrastructure/llm/ "
            "and register it here."
        )

    logger.info(
        "llm_provider_ready",
        provider=_provider.provider_name(),
        model=_provider.model_name(),
    )
    return _provider


def get_llm_provider() -> LLMProvider:
    """FastAPI dependency — returns the pre-initialised singleton."""
    if _provider is None:
        raise RuntimeError(
            "LLM provider not initialised. "
            "Call init_llm_provider() at startup, or set ANTHROPIC_API_KEY."
        )
    return _provider
