from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class AgentRun(BaseEntity):
    agent_type: str
    query: str
    workflow_run_id: str | None = None
    step_index: int = 0
    result_content: str | None = None
    confidence: float = 1.0
    reasoning: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    run_metadata: dict[str, Any] = field(default_factory=dict)
