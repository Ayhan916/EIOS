"""
EIOS Domain Model — Regulatory Change Monitoring (GAP-19)

Captures detected or manually logged changes to regulatory frameworks
(LkSG, CSDDD, CSRD, etc.) and tracks their impact on existing assessments
and compliance gaps.

Reference: M47 Regulatory Hub + GAP-19 implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .base_entity import BaseEntity
from .enums import RegulatoryChangeSeverity, RegulatoryChangeStatus


@dataclass(slots=True, kw_only=True)
class RegulatoryChange(BaseEntity):
    """A detected or manually registered regulatory change.

    Global changes (e.g. CSDDD Art. 8 amendment) have organization_id=None
    and are visible to all organisations. Org-specific entries can be created
    for custom jurisdictions.
    """

    organization_id: str | None = None  # None = global / shared

    framework_code: str = ""        # LkSG | CSDDD | CSRD | GDPR | …
    change_title: str = ""
    change_description: str = ""
    affected_article: str = ""      # e.g. "Art. 10 Abs. 2"
    effective_date: date | None = None

    severity: str = RegulatoryChangeSeverity.MODERATE.value
    change_status: str = RegulatoryChangeStatus.NEW.value

    source_name: str = ""           # EUR-Lex | Bundesanzeiger | ESMA | Manual
    source_url: str = ""

    # Scope filters used by the impact scanner
    affected_sectors: list[str] = field(default_factory=list)   # NACE 2-digit codes
    affected_frameworks: list[str] = field(default_factory=list)  # secondary frameworks

    impact_summary: str = ""        # filled after scan

    # Counts filled by the scanner
    impacted_assessment_count: int = 0
    impacted_gap_count: int = 0

    regulation_refs: str = ""       # e.g. "CSDDD Art. 10; OJ L 2024/1234"


@dataclass(slots=True, kw_only=True)
class RegulatoryChangeImpact(BaseEntity):
    """Link between a RegulatoryChange and one affected Assessment or ComplianceGap."""

    organization_id: str = ""
    change_id: str = ""

    # Exactly one of these is set
    assessment_id: str | None = None
    compliance_gap_id: str | None = None

    impact_type: str = "assessment_re_review"   # assessment_re_review | gap_update
    re_review_required: bool = True
    notification_sent: bool = False
    acknowledged_by_user_id: str | None = None
    acknowledged_at: datetime | None = None
