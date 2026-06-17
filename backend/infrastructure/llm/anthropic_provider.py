"""
EIOS Anthropic LLM Provider

Default provider implementation using the Anthropic Python SDK.
Treats Anthropic as a swappable provider, not an architectural dependency.

All agent code depends only on the LLMProvider Protocol defined in
application/ports/llm.py — never on this file directly.
"""

import structlog
from anthropic import AsyncAnthropic

from application.ports.llm import LLMResponse, Message

logger = structlog.get_logger(__name__)

PROVIDER_NAME = "anthropic"


class AnthropicLLMProvider:
    """Anthropic Messages API implementation of the LLMProvider protocol."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    def model_name(self) -> str:
        return self._model

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
        anthropic_messages = [{"role": m.role, "content": m.content} for m in messages]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)

        content = response.content[0].text if response.content else ""

        logger.debug(
            "llm_complete",
            provider=PROVIDER_NAME,
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )

        return LLMResponse(
            content=content,
            model=response.model,
            provider=PROVIDER_NAME,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason or "end_turn",
            raw=response,
        )
