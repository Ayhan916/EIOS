from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from application.agents.registry import AGENT_TYPES


class AgentRunRequest(BaseModel):
    agent_type: str = Field(description=f"One of: {', '.join(AGENT_TYPES)}")
    query: str = Field(min_length=1, max_length=10000)
    knowledge_chunks: list[str] = Field(default_factory=list)
    prior_outputs: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    id: str
    agent_type: str
    query: str
    result_content: Optional[str]
    confidence: float
    reasoning: Optional[str]
    llm_provider: Optional[str]
    llm_model: Optional[str]
    input_tokens: int
    output_tokens: int
    error: Optional[str]
    run_metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime
