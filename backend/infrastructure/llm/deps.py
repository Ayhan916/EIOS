"""
LLM provider factory and FastAPI dependency.

Provider is selected from config (LLM_PROVIDER env var).
Adding a new provider requires only: implementing LLMProvider Protocol + adding a branch here.

ADR-012 Multi-Model Routing:
  _provider           → Sonnet (Copilot, complex reasoning)
  _extraction_provider → Haiku  (metric/signal extraction, classification)
"""

import structlog

from application.ports.llm import LLMProvider
from shared.config import settings

logger = structlog.get_logger(__name__)

_provider: LLMProvider | None = None
_extraction_provider: LLMProvider | None = None


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

    elif name == "groq":
        from infrastructure.llm.groq_provider import GroqLLMProvider

        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        _provider = GroqLLMProvider(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{name}'. "
            "Supported values: anthropic, openai, groq. "
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


def init_extraction_llm_provider() -> LLMProvider:
    """Initialise the dedicated Haiku extraction provider (ADR-007).

    Always uses AnthropicLLMProvider with the extraction model (Haiku by default).
    Requires ANTHROPIC_API_KEY. Falls back to the main provider if key is absent.
    """
    global _extraction_provider
    if _extraction_provider is not None:
        return _extraction_provider

    if not settings.anthropic_api_key:
        logger.warning(
            "extraction_provider_fallback",
            reason="ANTHROPIC_API_KEY not set — extraction will use main LLM provider",
        )
        _extraction_provider = init_llm_provider()
        return _extraction_provider

    from infrastructure.llm.anthropic_provider import AnthropicLLMProvider

    _extraction_provider = AnthropicLLMProvider(
        api_key=settings.anthropic_api_key,
        model=settings.extraction_llm_model,
    )
    logger.info(
        "extraction_provider_ready",
        model=settings.extraction_llm_model,
    )
    return _extraction_provider


def get_extraction_llm_provider() -> LLMProvider:
    """Return the extraction LLM provider, lazily initialising if needed (ADR-007).

    Lazy init allows standalone scripts (run_extract_all.py) to call this
    without going through the FastAPI lifespan.
    """
    global _extraction_provider
    if _extraction_provider is None:
        return init_extraction_llm_provider()
    return _extraction_provider
