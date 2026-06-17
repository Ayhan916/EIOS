from typing import Any

from pydantic import BaseModel

from .base import EntityResponse


class ReportGenerateRequest(BaseModel):
    assessment_id: str


class ReportResponse(EntityResponse):
    assessment_id: str
    title: str
    generated_by: str
    organization_id: str | None = None
    format: str
    finding_count: int
    risk_count: int
    recommendation_count: int
    evidence_count: int
    content_snapshot: dict[str, Any] | None = None
