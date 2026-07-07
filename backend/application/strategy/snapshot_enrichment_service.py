"""M44.1 — Cross-module Digital Twin snapshot enrichment.

Pulls sustainability and financial ESG state from M42/M43 persistence
layers and merges them into a DigitalTwinSnapshotModel's fields.
All enrichment is additive — existing snapshot data is preserved.
Import errors from M42/M43 models are silently skipped so this module
is safe to call even when those modules are not yet present.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from infrastructure.persistence.models.strategy import DigitalTwinSnapshotModel


def _now() -> datetime:
    return datetime.now(UTC)


def _fetch_green_revenue(organization_id: str, session: Session) -> dict | None:
    try:
        from infrastructure.persistence.models.financial_esg import (
            GreenRevenueRecordModel,  # type: ignore[import]
        )

        row = (
            session.query(GreenRevenueRecordModel)
            .filter(GreenRevenueRecordModel.organization_id == organization_id)
            .order_by(desc(GreenRevenueRecordModel.created_at))
            .first()
        )
        if row:
            return {
                "green_revenue_amount": getattr(row, "green_revenue_amount", None),
                "green_revenue_pct": getattr(row, "green_revenue_pct", None),
                "reporting_period": getattr(row, "reporting_period", None),
            }
    except Exception:
        pass
    return None


def _fetch_taxonomy_alignment(organization_id: str, session: Session) -> dict | None:
    try:
        from infrastructure.persistence.models.financial_esg import (
            TaxonomyAlignmentAssessmentModel,  # type: ignore[import]
        )

        row = (
            session.query(TaxonomyAlignmentAssessmentModel)
            .filter(TaxonomyAlignmentAssessmentModel.organization_id == organization_id)
            .order_by(desc(TaxonomyAlignmentAssessmentModel.created_at))
            .first()
        )
        if row:
            return {
                "taxonomy_eligible_pct": getattr(row, "taxonomy_eligible_pct", None),
                "taxonomy_aligned_pct": getattr(row, "taxonomy_aligned_pct", None),
            }
    except Exception:
        pass
    return None


def enrich_snapshot(
    organization_id: str,
    snapshot: DigitalTwinSnapshotModel,
    session: Session,
) -> DigitalTwinSnapshotModel:
    """Merge M42/M43 state into snapshot.financial_esg_state (additive)."""
    state = dict(snapshot.financial_esg_state or {})

    green_rev = _fetch_green_revenue(organization_id, session)
    if green_rev:
        state["green_revenue"] = green_rev

    taxonomy = _fetch_taxonomy_alignment(organization_id, session)
    if taxonomy:
        state["taxonomy_alignment"] = taxonomy

    snapshot.financial_esg_state = state
    snapshot.updated_at = _now()
    session.flush()
    return snapshot
