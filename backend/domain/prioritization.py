"""
EIOS Domain Model — Prioritisation (GAP-18 / CSDDD Art. 10)

Persistent record of every prioritisation decision made for a supplier.
Provides the audit trail required by CSDDD Art. 10 ("documented and reasoned
decisions on prioritisation of adverse impacts").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class PrioritizationDecision(BaseEntity):
    """A scored, ranked, and auditable prioritisation record for one supplier.

    Columns map to CSDDD Art. 10 criteria:
      - severity_weight    : severity of the (potential) adverse impact
      - probability_weight : likelihood of occurrence
      - people_affected_weight : scale — number of people affected
    """

    organization_id: str = ""
    supplier_id: str = ""
    supplier_name: str = ""

    # CSDDD Art. 10 weighted inputs (each in range 0–4)
    severity_weight: float = 0.0
    probability_weight: float = 0.0
    people_affected_weight: float = 0.0

    # Computed output
    priority_score: float = 0.0   # severity*0.40 + probability*0.35 + people*0.25
    priority_rank: int = 0        # 1 = highest priority within the org

    # Capacity planning
    resource_capacity_per_quarter: int = 4  # how many audits/assessments the org can run

    # Human-readable justification (mandatory)
    reasoning: str = ""

    # Override by analyst
    overridden_manually: bool = False
    override_comment: str | None = None

    # Who triggered the computation / override
    decided_by_user_id: str = ""
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    regulation_refs: str = "CSDDD Art. 10; LkSG §5"
