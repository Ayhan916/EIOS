from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from application.workflows.registry import WORKFLOW_TYPES


class WorkflowRunRequest(BaseModel):
    workflow_type: str = Field(description=f"One of: {', '.join(WORKFLOW_TYPES)}")
    query: str = Field(min_length=1, max_length=10000)
    metadata: dict = Field(default_factory=dict)


class AgentStepSummary(BaseModel):
    agent_run_id: str
    agent_type: str
    step_index: int
    status: str
    input_tokens: int
    output_tokens: int
    error: Optional[str]


class WorkflowRunResponse(BaseModel):
    id: str
    workflow_type: str
    query: str
    verdict: Optional[str]
    verdict_reasoning: Optional[str]
    overall_risk_level: Optional[str]
    steps_completed: int
    total_steps: int
    total_input_tokens: int
    total_output_tokens: int
    error: Optional[str]
    # Structured extraction results
    assessment_id: Optional[str] = None
    finding_count: int = 0
    risk_count: int = 0
    recommendation_count: int = 0
    run_metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime
    steps: list[AgentStepSummary] = Field(default_factory=list)


class WorkflowTypeInfo(BaseModel):
    workflow_type: str
    description: str
    step_count: int
    agent_sequence: list[str]
