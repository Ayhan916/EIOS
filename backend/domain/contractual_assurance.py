"""Domain model — Contractual Assurance (CSDDD Art. 10).

Art. 10 requires companies to embed due-diligence obligations in supplier
contracts and cascade these requirements through the supply chain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContractClause:
    """A reusable DD clause template that can be assigned to suppliers."""
    id: str
    organization_id: str
    title: str
    clause_text: str
    category: str               # ClauseCategory
    cascade_required: bool      # must the supplier pass this clause to their own suppliers?
    is_mandatory: bool          # mandatory for all suppliers vs. optional
    version: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ContractAssurance:
    """Tracks one supplier's acceptance of one contractual clause."""
    id: str
    organization_id: str
    supplier_id: str
    clause_id: str
    status: str                     # AssuranceStatus
    accepted_at: datetime | None
    accepted_by: str | None         # analyst/user who recorded the acceptance
    document_ref: str | None        # contract file reference / URL
    notes: str | None
    cascade_confirmed: bool         # supplier confirmed they passed clause to their sub-suppliers
    cascade_confirmed_at: datetime | None
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ClauseAuditLog:
    """Immutable audit trail for assurance status changes."""
    id: str
    organization_id: str
    assurance_id: str
    changed_by: str
    from_status: str | None
    to_status: str
    note: str | None
    created_at: datetime
