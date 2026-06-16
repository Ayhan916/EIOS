from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class AgentRun(BaseEntity):
    agent_type: str
    query: str
    workflow_run_id: Optional[str] = None
    step_index: int = 0
    result_content: Optional[str] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None
    run_metadata: dict = field(default_factory=dict)
