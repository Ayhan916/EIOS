"""CSDDD-002 — DD-Governance domain models (Art. 7)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from .base_entity import BaseEntity
from .enums import DDPolicyStatus


@dataclass(slots=True, kw_only=True)
class DDPolicy(BaseEntity):
    """Due-Diligence-Politik — Art. 7 CSDDD."""

    organization_id: str
    title: str
    policy_status: DDPolicyStatus = DDPolicyStatus.DRAFT
    content_text: str = ""
    file_url: str | None = None
    approved_by: str = ""
    approved_role: str = ""
    valid_from: date | None = None
    published_at: datetime | None = None
    # computed: valid_from + 24 months; set on activation
    next_review_due: date | None = None
    is_public: bool = False
    public_token: str | None = None
    # which version of the policy (1, 2, 3 …)
    policy_version: int = 1
    # id of the policy this was cloned from (for review lineage)
    parent_policy_id: str | None = None

    def activate(self) -> None:
        from datetime import UTC

        self.policy_status = DDPolicyStatus.ACTIVE
        if self.valid_from is None:
            self.valid_from = datetime.now(UTC).date()
        # Art. 7 Abs. 4: review every 24 months
        self.next_review_due = date(
            self.valid_from.year + 2 if self.valid_from.month <= 12 else self.valid_from.year + 2,
            self.valid_from.month,
            self.valid_from.day,
        )

    @property
    def review_status(self) -> str:
        from datetime import UTC

        if self.policy_status != DDPolicyStatus.ACTIVE:
            return "inactive"
        if self.next_review_due is None:
            return "unknown"
        today = datetime.now(UTC).date()
        days_left = (self.next_review_due - today).days
        if days_left < 0:
            return "overdue"
        if days_left <= 30:
            return "due_soon_30"
        if days_left <= 60:
            return "due_soon_60"
        return "current"


@dataclass(slots=True, kw_only=True)
class CodeOfConduct(BaseEntity):
    """Verhaltenskodex — Art. 7 Abs. 2 CSDDD (Lieferanten + Mitarbeiter)."""

    organization_id: str
    title: str
    content_text: str = ""
    file_url: str | None = None
    coc_version: int = 1
    valid_from: date | None = None
    # acceptance expiry in months (12 or 24)
    acceptance_validity_months: int = 24
    is_active: bool = True
    linked_policy_id: str | None = None


@dataclass(slots=True, kw_only=True)
class CoCAcceptance(BaseEntity):
    """Unveränderliche Bestätigung eines Lieferanten — DSGVO-konform."""

    organization_id: str
    coc_id: str
    supplier_id: str
    coc_version: int
    accepted_at: datetime | None = None
    accepted_by_name: str = ""
    # DSGVO: nur Hash, nie rohe IP
    ip_hash: str | None = None
    expires_at: date | None = None

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
