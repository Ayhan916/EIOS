"""Domain models for CSDDD Art. 12 — Remedy Case Manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    source_grievance_id: UUID | None
    co_responsible_parties: list[str]
    closed_at: datetime | None
    closed_by: str | None
    closure_notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class RemedyBeneficiary:
    id: UUID
    remedy_case_id: UUID
    reference: str
    affected_type: AffectedPartyType
    promised_compensation: float | None
    received_compensation: float | None
    confirmation_date: datetime | None
    created_at: datetime


@dataclass
class RemedyAction:
    id: UUID
    remedy_case_id: UUID
    title: str
    description: str
    status: RemedyActionStatus
    responsible_party: str | None
    due_date: datetime | None
    completed_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class RemedyAuditLog:
    id: UUID
    remedy_case_id: UUID
    action: str
    performed_by: str
    details: str | None
    created_at: datetime
