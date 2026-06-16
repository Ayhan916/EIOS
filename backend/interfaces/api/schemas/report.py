from typing import Any, Optional

from pydantic import BaseModel

from .base import EntityResponse


class ReportGenerateRequest(BaseModel):
    assessment_id: str


class ReportResponse(EntityResponse):
    assessment_id: str
    title: str
    generated_by: str
    organization_id: Optional[str] = None
    format: str
    finding_count: int
    risk_count: int
    recommendation_count: int
    evidence_count: int
    content_snapshot: Optional[dict[str, Any]] = None
