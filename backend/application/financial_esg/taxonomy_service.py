"""M43 — Taxonomy Alignment Engine (EU Taxonomy).

All alignment percentages are deterministic:
  aligned_percent = aligned_revenue / total_revenue × 100
  eligible_percent = eligible_revenue / total_revenue × 100
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import FinancialESGError, _assert_org, _now
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    TAXONOMY_ASSESSMENT_STATUSES,
    TAXONOMY_FRAMEWORKS,
    TaxonomyAlignmentAssessmentModel,
)


def _compute_percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 4)


def create_taxonomy_assessment(
    organization_id: str,
    assessment_year: int,
    actor_id: str,
    session: Session,
    *,
    taxonomy_framework: str = "EU_TAXONOMY",
    eligible_activities: dict | None = None,
    aligned_activities: dict | None = None,
    total_revenue: float | None = None,
    total_capex: float | None = None,
    total_opex: float | None = None,
    justification: str | None = None,
) -> TaxonomyAlignmentAssessmentModel:
    if taxonomy_framework not in TAXONOMY_FRAMEWORKS:
        raise FinancialESGError(f"Invalid taxonomy_framework: {taxonomy_framework}")

    eligible_activities = eligible_activities or {}
    aligned_activities = aligned_activities or {}

    eligible_value = sum(
        float(v.get("amount", 0)) for v in eligible_activities.values()
        if isinstance(v, dict)
    )
    aligned_value = sum(
        float(v.get("amount", 0)) for v in aligned_activities.values()
        if isinstance(v, dict)
    )

    eligible_pct = _compute_percent(eligible_value, total_revenue or 0.0)
    aligned_pct = _compute_percent(aligned_value, total_revenue or 0.0)

    now = _now()
    rec = TaxonomyAlignmentAssessmentModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        taxonomy_framework=taxonomy_framework,
        assessment_year=assessment_year,
        eligible_activities=eligible_activities,
        aligned_activities=aligned_activities,
        eligible_percent=eligible_pct,
        aligned_percent=aligned_pct,
        justification=justification,
        assessment_status="DRAFT",
        total_revenue=total_revenue,
        total_capex=total_capex,
        total_opex=total_opex,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.taxonomy.assessed",
        actor_id=actor_id,
        resource_type="taxonomy_alignment_assessment",
        resource_id=rec.id,
        details={
            "assessment_year": assessment_year,
            "taxonomy_framework": taxonomy_framework,
            "aligned_percent": aligned_pct,
            "eligible_percent": eligible_pct,
        },
    )
    financial_esg_counters.record_taxonomy_assessment()
    return rec


def update_assessment_status(
    assessment_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> TaxonomyAlignmentAssessmentModel:
    if new_status not in TAXONOMY_ASSESSMENT_STATUSES:
        raise FinancialESGError(f"Invalid status: {new_status}")
    rec = session.get(TaxonomyAlignmentAssessmentModel, assessment_id)
    _assert_org(rec, organization_id, "Taxonomy assessment")
    if rec.assessment_status == "VERIFIED":
        raise FinancialESGError("Verified assessment cannot be changed")
    rec.assessment_status = new_status
    rec.updated_by = actor_id
    rec.updated_at = _now()
    session.flush()
    return rec


def list_taxonomy_assessments(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[TaxonomyAlignmentAssessmentModel]:
    return (
        session.query(TaxonomyAlignmentAssessmentModel)
        .filter(TaxonomyAlignmentAssessmentModel.organization_id == organization_id)
        .order_by(TaxonomyAlignmentAssessmentModel.assessment_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
