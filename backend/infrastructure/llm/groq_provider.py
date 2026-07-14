"""
EIOS Groq LLM Provider

Groq offers OpenAI-compatible inference at high speed with a free tier.
Uses the openai SDK pointed at Groq's base URL — no additional package needed.

To activate: set LLM_PROVIDER=groq and GROQ_API_KEY in .env
Recommended model: llama-3.3-70b-versatile (free tier, fast)
"""

import asyncio
import re

import structlog

from application.ports.llm import LLMResponse, Message

logger = structlog.get_logger(__name__)

PROVIDER_NAME = "groq"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Groq free-tier limits:
#   70B versatile:  30 RPM,  6 000 TPM,  100 000 TPD
#   8B instant:   1 000 RPM, 20 000 TPM, high daily quota (no practical cap)
#
# When the 70B daily quota is exhausted, automatically fall back to 8B so the
# Copilot stays functional. RPM/TPM errors wait and retry with the same model.

_FALLBACK_MODEL = "llama-3.1-8b-instant"
_MAX_RETRY_WAIT_S = 20.0  # stay inside 30s axios timeout
_MAX_ATTEMPTS = 3


class GroqLLMProvider:
    """Groq inference API via OpenAI-compatible client."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        except ImportError as exc:
            raise ImportError(
                "Groq provider requires the 'openai' package. Install it with: uv add openai"
            ) from exc
        self._model = model
        self._active_model = model  # may switch to fallback during a request

    def model_name(self) -> str:
        return self._active_model

    def provider_name(self) -> str:
        return PROVIDER_NAME

    async def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        current_model = self._model

        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.chat.completions.create(
                    model=current_model,
                    messages=openai_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                content = response.choices[0].message.content or ""
                usage = response.usage
                self._active_model = current_model

                return LLMResponse(
                    content=content,
                    model=response.model,
                    provider=PROVIDER_NAME,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    stop_reason=response.choices[0].finish_reason or "stop",
                    raw=response,
                )

            except Exception as exc:
                err = str(exc)
                is_rate_limit = "429" in err or "rate_limit_exceeded" in err
                is_daily_limit = "tokens per day" in err or "TPD" in err or "per day" in err
                is_last_attempt = attempt >= _MAX_ATTEMPTS - 1

                if is_rate_limit and is_daily_limit and current_model != _FALLBACK_MODEL:
                    # Daily quota exhausted → switch to fallback model immediately
                    logger.warning(
                        "groq_daily_limit_fallback",
                        primary_model=current_model,
                        fallback_model=_FALLBACK_MODEL,
                    )
                    current_model = _FALLBACK_MODEL
                    continue

                if is_rate_limit and not is_last_attempt:
                    # Transient RPM/TPM limit → wait and retry with same model
                    match = re.search(r"try again in (\d+(?:\.\d+)?)s", err)
                    raw_wait = float(match.group(1)) if match else 5.0
                    wait = min(raw_wait + 1.0, _MAX_RETRY_WAIT_S)
                    logger.warning(
                        "groq_rate_limit_retry",
                        attempt=attempt + 1,
                        wait_s=round(wait, 1),
                        model=current_model,
                    )
                    await asyncio.sleep(wait)
                    continue

                raise
