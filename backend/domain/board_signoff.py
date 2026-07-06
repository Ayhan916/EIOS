"""Domain model — Board Sign-off Trail (CSDDD Art. 22).

Art. 22 requires the management body (board of directors) to:
  - Approve the DD due diligence strategy and policy
  - Oversee implementation of DD obligations
  - Integrate DD into corporate strategy

All approvals and rejections are immutable audit records.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BoardSignoffRequest:
    """A sign-off request sent to one or more board members."""
    id: str
    organization_id: str
    title: str
    signoff_type: str               # BoardSignoffType
    entity_type: str | None         # the EIOS entity being approved
    entity_id: str | None
    description: str
    status: str                     # BoardSignoffStatus
    requested_by: str
    requested_at: datetime
    due_date: datetime | None
    approved_at: datetime | None
    approved_by: str | None
    approved_by_role: str | None    # BoardMemberRole
    rejection_reason: str | None
    document_ref: str | None        # link to the actual document
    created_at: datetime
    updated_at: datetime


@dataclass
class BoardDecision:
    """Immutable record of a single board member's decision on a request."""
    id: str
    organization_id: str
    request_id: str
    decision: str               # "approved" | "rejected"
    decided_by: str             # name or email of the board member
    decided_by_role: str        # BoardMemberRole
    comment: str | None
    decided_at: datetime
