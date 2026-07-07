"""M33.2 AI Copilot Audit & Governance domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class DetectedContradiction(BaseEntity):
    """A data contradiction detected pre-LLM during context assembly.

    Persisted so auditors can see what inconsistencies were present in the
    retrieved data at answer-generation time.
    """

    message_id: str
    organization_id: str
    contradiction_type: str  # ContradictionType value
    description: str
    involved_objects: list[Any] = field(default_factory=list)
    severity: str = "warning"
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, kw_only=True)
class CopilotCitationIntegrity(BaseEntity):
    """Per-citation integrity record for a Copilot answer.

    Captures whether a citation still exists in the platform, belongs to the
    tenant, and matches what was retrieved at answer time.
    """

    message_id: str
    organization_id: str
    citation_type: str
    object_id: str
    integrity_status: str  # CitationIntegrityStatus value
    citation_hash: str = ""
    citation_snapshot: dict[str, Any] = field(default_factory=dict)
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, kw_only=True)
class CopilotFeedback(BaseEntity):
    """User feedback on a Copilot assistant message."""

    message_id: str
    conversation_id: str
    organization_id: str
    user_id: str
    rating: str  # FeedbackRating value
    reason: str = ""
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, kw_only=True)
class CopilotAnswerReview(BaseEntity):
    """Executive review of a Copilot assistant message.

    Allows executives to flag answers as approved, misleading, or requiring
    investigation, creating a governed audit trail.
    """

    message_id: str
    conversation_id: str
    organization_id: str
    reviewer_id: str
    decision: str  # ReviewDecision value
    notes: str = ""
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, kw_only=True)
class CopilotAuditPackage(BaseEntity):
    """Immutable audit package for a Copilot answer.

    Contains the full reasoning chain: question → retrieval → context →
    prompt → model → answer → citations, hashed for tamper detection.
    """

    message_id: str
    organization_id: str
    package_hash: str
    json_payload: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    verification_status: str = "pending"  # AuditVerificationStatus value
    verified_at: datetime | None = None
