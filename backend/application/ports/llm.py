"""
EIOS LLM Provider Port Interface

The canonical abstraction for all LLM integrations.
Agents and domain logic depend ONLY on this protocol.
Concrete providers (Anthropic, OpenAI, local models) live in infrastructure/llm/.

Design principles (Founder decision, M6):
- Open-source-first, no vendor lock-in
- Anthropic is the default provider implementation, not an architectural dependency
- Providers are swappable without changes to agent or domain logic
"""

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    raw: Optional[object] = field(default=None, repr=False)


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[Message],
        *,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...

    def model_name(self) -> str: ...

    def provider_name(self) -> str: ...
