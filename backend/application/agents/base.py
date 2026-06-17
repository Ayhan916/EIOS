"""
EIOS Agent Base

All 10 canonical EIOS agents inherit from BaseAgent.
Agents depend only on LLMProvider (the abstract protocol) — never on concrete providers.

Flow: AgentContext → BaseAgent.run() → LLMProvider.complete() → AgentResult
"""

from dataclasses import dataclass, field

from application.ports.llm import LLMProvider, LLMResponse, Message


@dataclass
class AgentContext:
    """Inputs provided to an agent at invocation time."""

    query: str
    knowledge_chunks: list[str] = field(default_factory=list)
    prior_outputs: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # type: ignore[type-arg]


@dataclass
class AgentResult:
    """Structured output from an agent run."""

    content: str
    agent_type: str
    confidence: float = 1.0
    reasoning: str | None = None
    metadata: dict = field(default_factory=dict)  # type: ignore[type-arg]
    llm_response: LLMResponse | None = None


class BaseAgent:
    """
    Abstract base for all EIOS agents.

    Subclasses must define:
      - agent_type: str — canonical identifier (e.g. "esg_assessment")
      - system_prompt: str — domain-specific instructions for the LLM
      - run(): build messages and call self._complete()
    """

    agent_type: str = "base"
    system_prompt: str = "You are an EIOS agent."

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def _build_knowledge_block(self, chunks: list[str]) -> str:
        if not chunks:
            return ""
        formatted = "\n\n---\n\n".join(
            f"[Chunk {i + 1}]\n{chunk}" for i, chunk in enumerate(chunks)
        )
        return f"\n\n<knowledge>\n{formatted}\n</knowledge>"

    def _build_prior_outputs_block(self, outputs: list[str]) -> str:
        if not outputs:
            return ""
        formatted = "\n\n---\n\n".join(
            f"[Prior Output {i + 1}]\n{output}" for i, output in enumerate(outputs)
        )
        return f"\n\n<prior_agent_outputs>\n{formatted}\n</prior_agent_outputs>"

    async def _complete(
        self,
        messages: list[Message],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        return await self._provider.complete(
            messages,
            system=self.system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
