from typing import Optional

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel
from .base import EntityResponse


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    category: str = ""
    assessment_id: Optional[str] = None
    sector_id: Optional[str] = None
    probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    impact: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    reasoning: Optional[str] = None
    uncertainty: Optional[str] = None


class RiskResponse(EntityResponse):
    title: str
    description: str
    risk_level: str
    category: str
    assessment_id: Optional[str] = None
    sector_id: Optional[str] = None
    probability: Optional[float] = None
    impact: Optional[float] = None
    confidence: str
    reasoning: Optional[str] = None
    uncertainty: Optional[str] = None
