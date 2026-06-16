from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class WorkflowRun(BaseEntity):
    workflow_type: str
    query: str
    steps_completed: int = 0
    total_steps: int = 0
    verdict: Optional[str] = None
    verdict_reasoning: Optional[str] = None
    overall_risk_level: Optional[str] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: Optional[str] = None
    organization_id: Optional[str] = None
    # Structured entity extraction results
    assessment_id: Optional[str] = None
    finding_count: int = 0
    risk_count: int = 0
    recommendation_count: int = 0
    run_metadata: dict = field(default_factory=dict)
