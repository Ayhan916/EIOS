from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel

from .base import EntityResponse


class FindingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    assessment_id: str
    category: str = ""
    severity: RiskLevel = RiskLevel.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reasoning: str | None = None
    uncertainty: str | None = None


class FindingResponse(EntityResponse):
    title: str
    description: str
    assessment_id: str
    category: str
    severity: str
    confidence: str
    reasoning: str | None = None
    uncertainty: str | None = None
