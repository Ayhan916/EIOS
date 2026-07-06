"""Domain models for CSDDD Art. 12 — Remedy Case Manager."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.enums import (
    AffectedPartyType,
    ImpactCausation,
    RemedyActionStatus,
    RemedyCaseStatus,
    RemedyType,
)


@dataclass
class RemedyCase:
    id: UUID
    organization_id: UUID
    title: str
    description: str
    incident_date: datetime
    affected_count: int
    affected_type: AffectedPartyType
    rights: list[str]
    remedy_types: list[RemedyType]
    severity_score: float
    impact_causation: ImpactCausation
    status: RemedyCaseStatus
    source_grievance_id: Optional[UUID]
    co_responsible_parties: list[str]
    closed_at: Optional[datetime]
    closed_by: Optional[str]
    closure_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class RemedyBeneficiary:
    id: UUID
    remedy_case_id: UUID
    reference: str
    affected_type: AffectedPartyType
    promised_compensation: Optional[float]
    received_compensation: Optional[float]
    confirmation_date: Optional[datetime]
    created_at: datetime


@dataclass
class RemedyAction:
    id: UUID
    remedy_case_id: UUID
    title: str
    description: str
    status: RemedyActionStatus
    responsible_party: Optional[str]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class RemedyAuditLog:
    id: UUID
    remedy_case_id: UUID
    action: str
    performed_by: str
    details: Optional[str]
    created_at: datetime
