from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel
from .base import EntityResponse


class RecommendationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    priority: RiskLevel = RiskLevel.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reasoning: Optional[str] = None
    action_required: bool = True
    due_date: Optional[datetime] = None


class RecommendationResponse(EntityResponse):
    title: str
    description: str
    priority: str
    confidence: str
    reasoning: Optional[str] = None
    action_required: bool
    due_date: Optional[datetime] = None
    approved_by: Optional[str] = None
