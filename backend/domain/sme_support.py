"""Domain model — SME Support Tracker (CSDDD Art. 10 Abs. 2 lit. b).

Art. 10 requires large companies to offer targeted, proportionate support to
SME suppliers that might otherwise be unable to meet DD requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SMEProfile:
    """EU SME classification metadata for a supplier."""

    id: str
    organization_id: str
    supplier_id: str
    classification: str  # SMEClassification
    employee_count: int | None
    annual_revenue_eur: float | None
    is_confirmed: bool  # human-verified classification
    confirmed_by: str | None
    confirmed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class SupportProgram:
    """A support program for one SME supplier — may contain multiple measures."""

    id: str
    organization_id: str
    supplier_id: str
    title: str
    description: str
    status: str  # SupportProgramStatus
    start_date: datetime | None
    end_date: datetime | None
    responsible_user: str | None
    total_budget_eur: float | None
    spent_budget_eur: float
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class SupportMeasure:
    """A single support action within a program."""

    id: str
    organization_id: str
    program_id: str
    title: str
    support_type: str  # SupportType
    status: str  # SupportMeasureStatus
    description: str | None
    due_date: datetime | None
    completed_at: datetime | None
    cost_eur: float | None
    impact_notes: str | None  # qualitative impact after completion
    created_at: datetime
    updated_at: datetime
