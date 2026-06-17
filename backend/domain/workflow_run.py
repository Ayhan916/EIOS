from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class WorkflowRun(BaseEntity):
    workflow_type: str
    query: str
    steps_completed: int = 0
    total_steps: int = 0
    verdict: str | None = None
    verdict_reasoning: str | None = None
    overall_risk_level: str | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: str | None = None
    organization_id: str | None = None
    # Structured entity extraction results
    assessment_id: str | None = None
    finding_count: int = 0
    risk_count: int = 0
    recommendation_count: int = 0
    run_metadata: dict[str, Any] = field(default_factory=dict)
