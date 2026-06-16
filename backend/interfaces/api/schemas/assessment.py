from typing import Optional

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel
from .base import EntityResponse


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    assessment_type: str = ""
    scope: str = ""
    sector_id: Optional[str] = None
    methodology: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH


class AssessmentResponse(EntityResponse):
    title: str
    description: str
    assessment_type: str
    scope: str
    sector_id: Optional[str] = None
    methodology: Optional[str] = None
    confidence: str
    approved_by: Optional[str] = None
    quality_score: Optional[float] = None
