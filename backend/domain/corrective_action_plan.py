"""Corrective Action Plan (CAP) domain (GAP-20).

Lifecycle:
  DRAFT → COMMITTED (supplier commits to the plan)
       → IN_PROGRESS (work underway)
       → EVIDENCE_SUBMITTED (supplier uploads evidence)
       → VERIFIED (analyst confirms evidence sufficient)
       → CLOSED (finding resolved, CAP archived)

   OR: DRAFT/any → OVERDUE (computed flag when deadline < today and not closed/verified)

Security:
  - organization_id is MANDATORY on every CAP — never omit from queries
  - Agents MUST NOT: close_cap(), verify_cap(), or call any status-change endpoint
  - Only human analyst/admin API calls may advance status
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class CorrectiveActionPlan(BaseEntity):
    """A structured remediation plan linked to a single Finding."""

    finding_id: str = ""
    organization_id: str = ""

    title: str = ""
    description: str = ""
    responsible_party: str = ""
    deadline: date | None = None

    # Status: DRAFT | COMMITTED | IN_PROGRESS | EVIDENCE_SUBMITTED | VERIFIED | CLOSED
    cap_status: str = "DRAFT"

    # Supplier-provided evidence (submitted via supplier portal or analyst)
    evidence_note: str = ""
    evidence_file_url: str | None = None
    evidence_submitted_at: datetime | None = None

    # Analyst verification
    verification_note: str = ""
    verified_by_user_id: str | None = None
    verified_at: datetime | None = None
    insufficient_reason: str = ""  # set when analyst marks evidence insufficient

    closed_at: datetime | None = None
    closed_by_user_id: str | None = None

    @property
    def is_overdue(self) -> bool:
        if self.cap_status in ("VERIFIED", "CLOSED"):
            return False
        return self.deadline is not None and self.deadline < date.today()

    @property
    def overdue_days(self) -> int:
        if not self.is_overdue or self.deadline is None:
            return 0
        return (date.today() - self.deadline).days
