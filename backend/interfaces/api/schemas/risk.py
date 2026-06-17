from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel

from .base import EntityResponse


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    category: str = ""
    assessment_id: str | None = None
    sector_id: str | None = None
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    impact: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    reasoning: str | None = None
    uncertainty: str | None = None


class RiskResponse(EntityResponse):
    title: str
    description: str
    risk_level: str
    category: str
    assessment_id: str | None = None
    sector_id: str | None = None
    probability: float | None = None
    impact: float | None = None
    confidence: str
    reasoning: str | None = None
    uncertainty: str | None = None
