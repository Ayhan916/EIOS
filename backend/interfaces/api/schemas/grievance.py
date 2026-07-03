"""Pydantic schemas for Grievance Mechanism — LkSG §8 / CSDDD Art. 14.

Security rules enforced here:
- submitted_by_email and submitted_by_name are WRITE-ONLY (not in any response schema)
- GrievanceReportResponse never exposes reporter identity
- GrievanceReportPublicResponse only shows status + reference code (for public tracking)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Public submit (no auth required) ──────────────────────────────────────────

class GrievanceSubmitRequest(BaseModel):
    """Public submission — submitted by external party via /grievance page."""

    organization_id: str = Field(..., description="Target organization ID (embedded in public page URL)")
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=20, max_length=10000)
    category: str = Field(default="other")

    # Voluntary contact — if provided, stored confidentially for blind reply
    submitted_by_email: Optional[str] = Field(default=None, max_length=320)
    submitted_by_name: Optional[str] = Field(default=None, max_length=255)
    related_supplier_name: Optional[str] = Field(default=None, max_length=500)


class GrievanceSubmitResponse(BaseModel):
    """Returned immediately after public submission — only safe fields."""

    reference_code: str
    message: str = (
        "Your report has been received. Use the reference code to check status. "
        "Your identity is protected and will not be shared with the subject of the report."
    )
    status: str = "received"


class GrievanceStatusCheckResponse(BaseModel):
    """Public status check by reference code — no internal data exposed."""

    reference_code: str
    status: str
    category: str
    submitted_at: datetime
    last_updated: datetime


# ── Internal management (analyst+ auth required) ───────────────────────────────

class GrievanceReportResponse(BaseModel):
    """Internal view — reporter identity intentionally omitted."""

    id: str
    organization_id: str
    category: str
    grievance_status: str
    title: str
    description: str

    is_anonymous: bool
    anonymized_reference_code: str

    related_supplier_id: Optional[str]
    assigned_to_user_id: Optional[str]
    reviewer_notes: Optional[str]
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]
    regulation_refs: str
    linked_finding_id: Optional[str]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GrievanceStatusUpdate(BaseModel):
    """Analyst updates status + optional notes."""

    grievance_status: str
    reviewer_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to_user_id: Optional[str] = None


class GrievanceSummary(BaseModel):
    """Aggregated counts for LkSG §10 reporting."""

    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
