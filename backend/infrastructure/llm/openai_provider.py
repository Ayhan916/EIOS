"""
EIOS OpenAI LLM Provider

Ready-to-activate provider implementation for OpenAI models.
Requires: pip install openai>=1.0.0 and OPENAI_API_KEY in environment.

To activate: set LLM_PROVIDER=openai and OPENAI_API_KEY in .env
"""

from application.ports.llm import LLMResponse, Message

PROVIDER_NAME = "openai"


class OpenAILLMProvider:
    """OpenAI Chat Completions API implementation of the LLMProvider protocol."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore[import]

            self._client = AsyncOpenAI(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "OpenAI provider requires the 'openai' package. Install it with: uv add openai"
            ) from exc
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

        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            content=content,
            model=response.model,
            provider=PROVIDER_NAME,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            stop_reason=response.choices[0].finish_reason or "stop",
            raw=response,
        )
