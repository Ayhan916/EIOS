from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel

from .base import EntityResponse


class RecommendationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    priority: RiskLevel = RiskLevel.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reasoning: str | None = None
    action_required: bool = True
    due_date: datetime | None = None


class RecommendationResponse(EntityResponse):
    title: str
    description: str
    priority: str
    confidence: str
    reasoning: str | None = None
    action_required: bool
    due_date: datetime | None = None
    approved_by: str | None = None
