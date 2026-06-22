"""M43 — Enterprise Financial ESG Rollups.

Aggregates financial ESG data across all organizations within an enterprise
hierarchy entity via SQL GROUP BY — no N+1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.financial_esg import (
    CarbonCostModelRecord,
    GreenRevenueRecordModel,
    SustainableFinanceInstrumentModel,
    TaxonomyAlignmentAssessmentModel,
    ValueCreationInitiativeModel,
    CapitalMarketsAssessmentModel,
)
from application.financial_esg.kpi_service import FinancialESGError, _now

EntityType = Literal["enterprise", "business_unit", "legal_entity", "region"]


@dataclass
class CarbonEconomicsRollup:
    total_carbon_cost: float = 0.0
    total_regulatory_exposure: float = 0.0
    total_avoided_cost: float = 0.0
    model_count: int = 0


@dataclass
class GreenRevenueRollup:
    total_green_amount: float = 0.0
    avg_green_percent: float = 0.0
    record_count: int = 0


@dataclass
class TaxonomyRollup:
    avg_aligned_percent: float | None = None
    avg_eligible_percent: float | None = None
    assessment_count: int = 0


@dataclass
class FinanceRollup:
    total_exposure: float = 0.0
    instrument_count: int = 0
    breached_count: int = 0


@dataclass
class ValueCreationRollup:
    total_investment: float = 0.0
    total_realized_value: float = 0.0
    initiative_count: int = 0
    avg_roi_percent: float | None = None


@dataclass
class FinancialRollupSummary:
    entity_type: str
    entity_id: str
    organization_ids: list[str] = field(default_factory=list)
    carbon_economics: CarbonEconomicsRollup = field(default_factory=CarbonEconomicsRollup)
    green_revenue: GreenRevenueRollup = field(default_factory=GreenRevenueRollup)
    taxonomy: TaxonomyRollup = field(default_factory=TaxonomyRollup)
    finance: FinanceRollup = field(default_factory=FinanceRollup)
    value_creation: ValueCreationRollup = field(default_factory=ValueCreationRollup)
    computed_at: str = ""


def _org_ids_for_entity(entity_type: EntityType, entity_id: str, session: Session) -> list[str]:
    col_map = {
        "enterprise": "enterprise_id",
        "business_unit": "business_unit_id",
        "legal_entity": "legal_entity_id",
        "region": "region_id",
    }
    col = getattr(OrganizationModel, col_map[entity_type])
    rows = session.query(OrganizationModel.id).filter(col == entity_id).all()
    return [r.id for r in rows]


def _carbon_rollup(org_ids: list[str], session: Session) -> CarbonEconomicsRollup:
    if not org_ids:
        return CarbonEconomicsRollup()
    row = (
        session.query(
            func.sum(CarbonCostModelRecord.total_carbon_cost).label("cost"),
            func.sum(CarbonCostModelRecord.regulatory_exposure).label("reg"),
            func.sum(CarbonCostModelRecord.avoided_cost).label("avoided"),
            func.count(CarbonCostModelRecord.id).label("cnt"),
        )
        .filter(CarbonCostModelRecord.organization_id.in_(org_ids))
        .one()
    )
    return CarbonEconomicsRollup(
        total_carbon_cost=round(float(row.cost or 0), 4),
        total_regulatory_exposure=round(float(row.reg or 0), 4),
        total_avoided_cost=round(float(row.avoided or 0), 4),
        model_count=int(row.cnt or 0),
    )


def _green_revenue_rollup(org_ids: list[str], session: Session) -> GreenRevenueRollup:
    if not org_ids:
        return GreenRevenueRollup()
    row = (
        session.query(
            func.sum(GreenRevenueRecordModel.amount).label("green"),
            func.avg(GreenRevenueRecordModel.green_revenue_percent).label("avg_pct"),
            func.count(GreenRevenueRecordModel.id).label("cnt"),
        )
        .filter(
            GreenRevenueRecordModel.organization_id.in_(org_ids),
            GreenRevenueRecordModel.alignment_status.in_(["ALIGNED", "ELIGIBLE"]),
        )
        .one()
    )
    return GreenRevenueRollup(
        total_green_amount=round(float(row.green or 0), 4),
        avg_green_percent=round(float(row.avg_pct or 0), 4),
        record_count=int(row.cnt or 0),
    )


def _taxonomy_rollup(org_ids: list[str], session: Session) -> TaxonomyRollup:
    if not org_ids:
        return TaxonomyRollup()
    row = (
        session.query(
            func.avg(TaxonomyAlignmentAssessmentModel.aligned_percent).label("avg_aligned"),
            func.avg(TaxonomyAlignmentAssessmentModel.eligible_percent).label("avg_eligible"),
            func.count(TaxonomyAlignmentAssessmentModel.id).label("cnt"),
        )
        .filter(TaxonomyAlignmentAssessmentModel.organization_id.in_(org_ids))
        .one()
    )
    if not row.cnt:
        return TaxonomyRollup()
    return TaxonomyRollup(
        avg_aligned_percent=round(float(row.avg_aligned), 4) if row.avg_aligned is not None else None,
        avg_eligible_percent=round(float(row.avg_eligible), 4) if row.avg_eligible is not None else None,
        assessment_count=int(row.cnt),
    )


def _finance_rollup(org_ids: list[str], session: Session) -> FinanceRollup:
    if not org_ids:
        return FinanceRollup()
    row = (
        session.query(
            func.sum(SustainableFinanceInstrumentModel.amount).label("total"),
            func.count(SustainableFinanceInstrumentModel.id).label("cnt"),
        )
        .filter(SustainableFinanceInstrumentModel.organization_id.in_(org_ids))
        .one()
    )
    breached = (
        session.query(func.count(SustainableFinanceInstrumentModel.id))
        .filter(
            SustainableFinanceInstrumentModel.organization_id.in_(org_ids),
            SustainableFinanceInstrumentModel.covenant_status == "BREACHED",
        )
        .scalar() or 0
    )
    return FinanceRollup(
        total_exposure=round(float(row.total or 0), 4),
        instrument_count=int(row.cnt or 0),
        breached_count=int(breached),
    )


def _value_creation_rollup(org_ids: list[str], session: Session) -> ValueCreationRollup:
    if not org_ids:
        return ValueCreationRollup()
    row = (
        session.query(
            func.sum(ValueCreationInitiativeModel.investment_amount).label("inv"),
            func.sum(ValueCreationInitiativeModel.realized_value).label("real"),
            func.avg(ValueCreationInitiativeModel.roi_percent).label("avg_roi"),
            func.count(ValueCreationInitiativeModel.id).label("cnt"),
        )
        .filter(ValueCreationInitiativeModel.organization_id.in_(org_ids))
        .one()
    )
    return ValueCreationRollup(
        total_investment=round(float(row.inv or 0), 4),
        total_realized_value=round(float(row.real or 0), 4),
        initiative_count=int(row.cnt or 0),
        avg_roi_percent=round(float(row.avg_roi), 4) if row.avg_roi is not None else None,
    )


def compute_financial_rollup(
    entity_type: EntityType,
    entity_id: str,
    actor_id: str,
    session: Session,
) -> FinancialRollupSummary:
    if entity_type not in ("enterprise", "business_unit", "legal_entity", "region"):
        raise FinancialESGError(f"Invalid entity_type: {entity_type}")

    org_ids = _org_ids_for_entity(entity_type, entity_id, session)
    summary = FinancialRollupSummary(
        entity_type=entity_type,
        entity_id=entity_id,
        organization_ids=org_ids,
        carbon_economics=_carbon_rollup(org_ids, session),
        green_revenue=_green_revenue_rollup(org_ids, session),
        taxonomy=_taxonomy_rollup(org_ids, session),
        finance=_finance_rollup(org_ids, session),
        value_creation=_value_creation_rollup(org_ids, session),
        computed_at=_now().isoformat(),
    )
    emit_audit_event(
        session=session,
        event_type="financial_esg.rollup.computed",
        actor_id=actor_id,
        resource_type=f"financial_rollup_{entity_type}",
        resource_id=entity_id,
        details={"organization_count": len(org_ids)},
    )
    return summary
