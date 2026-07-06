"""CSDDD-001 — Stakeholder Engagement domain models (Art. 13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .base_entity import BaseEntity
from .enums import ConsultationBarrier, ConsultationFormat, CSDDDRight, StakeholderType


@dataclass(slots=True, kw_only=True)
class Stakeholder(BaseEntity):
    organization_id: str
    name: str
    stakeholder_type: StakeholderType = StakeholderType.OTHER
    contact_email: str | None = None
    language: str = "de"
    # JSON-stored arrays (serialised as comma-separated strings in SQLite, JSON in PG)
    activity_chain_ids: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    risk_topics: list[str] = field(default_factory=list)
    # Art. 13 Abs. 1 mandatory: why is this party considered "affected"?
    justification: str = ""


@dataclass(slots=True, kw_only=True)
class StakeholderConsultation(BaseEntity):
    organization_id: str
    stakeholder_ids: list[str] = field(default_factory=list)
    consultation_date: date | None = None
    format: ConsultationFormat = ConsultationFormat.MEETING
    topics: list[str] = field(default_factory=list)
    description: str = ""
    outcomes: str = ""
    # Art. 13 Abs. 1: participation barriers must be explicitly documented
    barrier: ConsultationBarrier = ConsultationBarrier.NONE
    barrier_notes: str = ""
    # Optional links to DD artefacts
    linked_risk_id: str | None = None
    linked_finding_id: str | None = None
    linked_cap_id: str | None = None


@dataclass(slots=True, kw_only=True)
class StakeholderFeedback(BaseEntity):
    consultation_id: str
    organization_id: str
    risk_assessment: int = 3  # 1–5 scale
    affected_rights: list[str] = field(default_factory=list)
    description: str = ""
    wants_contact: bool = False
    # PII: never returned in API responses — admin only
    submitted_by_email: str | None = None
    submitted_by_name: str | None = None
    submitter_ip: str | None = None
