"""
EIOS Groq LLM Provider

Groq offers OpenAI-compatible inference at high speed with a free tier.
Uses the openai SDK pointed at Groq's base URL — no additional package needed.

To activate: set LLM_PROVIDER=groq and GROQ_API_KEY in .env
Recommended model: llama-3.3-70b-versatile (free tier, fast)
"""

from application.ports.llm import LLMResponse, Message

PROVIDER_NAME = "groq"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


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
