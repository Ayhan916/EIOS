from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel

from .base import EntityResponse


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    assessment_type: str = ""
    scope: str = ""
    sector_id: str | None = None
    methodology: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH


class AssessmentResponse(EntityResponse):
    title: str
    description: str
    assessment_type: str
    scope: str
    sector_id: str | None = None
    methodology: str | None = None
    confidence: str
    approved_by: str | None = None
    quality_score: float | None = None
    # Review workflow (M26)
    review_status: str = "Draft"
    assigned_reviewer_id: str | None = None
    review_due_date: datetime | None = None
