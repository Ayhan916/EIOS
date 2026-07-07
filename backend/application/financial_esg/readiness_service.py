"""M43 — Capital Markets Readiness and Investor Disclosure Packages."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import (
    FinancialESGConflict,
    FinancialESGError,
    _assert_org,
    _now,
)
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    READINESS_STATUSES,
    CapitalMarketsAssessmentModel,
    InvestorDisclosurePackageModel,
)


def _compute_overall_readiness(*statuses: str) -> str:
    if all(s == "READY" for s in statuses):
        return "READY"
    if all(s == "NOT_READY" for s in statuses):
        return "NOT_READY"
    return "PARTIAL"


def create_capital_markets_assessment(
    organization_id: str,
    actor_id: str,
    session: Session,
    *,
    disclosure_readiness: str = "NOT_READY",
    assurance_readiness: str = "NOT_READY",
    taxonomy_readiness: str = "NOT_READY",
    kpi_readiness: str = "NOT_READY",
    assessment_notes: dict | None = None,
) -> CapitalMarketsAssessmentModel:
    for label, val in [
        ("disclosure_readiness", disclosure_readiness),
        ("assurance_readiness", assurance_readiness),
        ("taxonomy_readiness", taxonomy_readiness),
        ("kpi_readiness", kpi_readiness),
    ]:
        if val not in READINESS_STATUSES:
            raise FinancialESGError(f"Invalid {label}: {val}")

    overall = _compute_overall_readiness(
        disclosure_readiness, assurance_readiness, taxonomy_readiness, kpi_readiness
    )
    now = _now()
    rec = CapitalMarketsAssessmentModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        disclosure_readiness=disclosure_readiness,
        assurance_readiness=assurance_readiness,
        taxonomy_readiness=taxonomy_readiness,
        kpi_readiness=kpi_readiness,
        overall_readiness=overall,
        assessment_notes=assessment_notes or {},
        assessed_at=now,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.capital_markets.assessed",
        actor_id=actor_id,
        resource_type="capital_markets_assessment",
        resource_id=rec.id,
        details={"overall_readiness": overall},
    )
    financial_esg_counters.record_capital_markets_assessment()
    return rec


def list_capital_markets_assessments(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[CapitalMarketsAssessmentModel]:
    return (
        session.query(CapitalMarketsAssessmentModel)
        .filter(CapitalMarketsAssessmentModel.organization_id == organization_id)
        .order_by(CapitalMarketsAssessmentModel.assessed_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def generate_disclosure_package(
    organization_id: str,
    title: str,
    period_start: datetime,
    period_end: datetime,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    esg_kpi_snapshot: dict | None = None,
    taxonomy_snapshot: dict | None = None,
    climate_metrics_snapshot: dict | None = None,
    assurance_status_snapshot: dict | None = None,
    sustainability_targets_snapshot: dict | None = None,
) -> InvestorDisclosurePackageModel:
    now = _now()
    pkg = InvestorDisclosurePackageModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        description=description,
        period_start=period_start,
        period_end=period_end,
        esg_kpi_snapshot=esg_kpi_snapshot or {},
        taxonomy_snapshot=taxonomy_snapshot or {},
        climate_metrics_snapshot=climate_metrics_snapshot or {},
        assurance_status_snapshot=assurance_status_snapshot or {},
        sustainability_targets_snapshot=sustainability_targets_snapshot or {},
        is_final=False,
        finalized_at=None,
        finalized_by=None,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(pkg)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.disclosure_package.generated",
        actor_id=actor_id,
        resource_type="investor_disclosure_package",
        resource_id=pkg.id,
        details={
            "title": title,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
    )
    financial_esg_counters.record_disclosure_package()
    return pkg


def finalize_disclosure_package(
    package_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> InvestorDisclosurePackageModel:
    pkg = session.get(InvestorDisclosurePackageModel, package_id)
    _assert_org(pkg, organization_id, "Disclosure package")
    if pkg.is_final:
        raise FinancialESGConflict("Disclosure package is already finalized")
    pkg.is_final = True
    pkg.finalized_at = _now()
    pkg.finalized_by = actor_id
    pkg.updated_by = actor_id
    pkg.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.disclosure_package.finalized",
        actor_id=actor_id,
        resource_type="investor_disclosure_package",
        resource_id=package_id,
        details={"finalized_at": pkg.finalized_at.isoformat()},
    )
    return pkg


def list_disclosure_packages(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[InvestorDisclosurePackageModel]:
    return (
        session.query(InvestorDisclosurePackageModel)
        .filter(InvestorDisclosurePackageModel.organization_id == organization_id)
        .order_by(InvestorDisclosurePackageModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
