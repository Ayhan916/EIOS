"""Self-Improvement Loop domain (GAP-05).

ImprovementProposal lifecycle:
  DRAFT → APPROVED (Founder) → IN_PROGRESS (team) → VERIFIED (after-benchmark)
  DRAFT → REJECTED (Founder)

AI agents MUST NOT auto-approve, auto-implement, or auto-verify proposals.
All status transitions require explicit human action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ImprovementProposal(BaseEntity):
    """A platform weakness detected by the Evaluation Engine with a proposed fix."""

    # ── Weakness classification ──────────────────────────────────────────────
    weakness_type: str = ""       # see WeaknessType enum below
    affected_module: str = ""     # benchmark module name or "global"
    current_value: float = 0.0    # e.g. accuracy=0.75
    target_value: float = 0.0     # e.g. accuracy=0.90
    expected_impact: float = 0.0  # absolute improvement (0–1)
    priority_score: float = 0.0   # higher = more urgent; deterministic

    # ── Human-readable content ───────────────────────────────────────────────
    title: str = ""
    description: str = ""
    suggested_action: str = ""

    # ── Approval workflow ────────────────────────────────────────────────────
    # Agents NEVER set these — only human API calls may change status
    approval_status: str = "DRAFT"        # DRAFT|APPROVED|IN_PROGRESS|VERIFIED|REJECTED
    approved_by_user_id: str | None = None
    approved_at: datetime | None = None
    rejected_by_user_id: str | None = None
    rejected_at: datetime | None = None
    reject_reason: str | None = None

    # ── Verification ─────────────────────────────────────────────────────────
    before_evaluation_run_id: str | None = None
    after_evaluation_run_id: str | None = None
    verified_improvement: float | None = None  # actual delta after implementation
    verified_at: datetime | None = None
