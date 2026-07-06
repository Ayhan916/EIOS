"""Domain model — ESAP Export (CSDDD-009, Art. 16 Abs. 2).

Art. 16 CSDDD requires public reporting on DD measures. From ca. 2031,
large companies must submit reports to ESAP (European Single Access Point)
in machine-readable format per EU Regulation 2023/2859.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ESAPSubmission:
    """Manual record of an ESAP submission for audit trail."""
    id: str
    organization_id: str
    report_year: int
    export_format: str             # ESAPExportFormat
    status: str                    # ESAPSubmissionStatus
    submitted_at: datetime | None
    submitted_by: str | None
    confirmation_reference: str | None
    notes: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ESAPExportBundle:
    """Structured ESAP-ready export document (Art. 16 fields)."""
    organization_id: str
    report_year: int
    generated_at: datetime
    schema_version: str
    # Art. 16 required sections
    dd_policy_description: str
    risks_summary: list[dict]      # top risks
    actions_summary: list[dict]    # CAPs + remedy cases
    board_approvals: list[dict]    # board sign-offs
    effectiveness_summary: str
    stakeholder_consultation: str
    # Validation
    missing_fields: list[str]
    is_valid: bool
