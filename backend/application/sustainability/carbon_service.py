"""Carbon Accounting — emission sources, carbon inventory, and calculations.

All calculations are deterministic:
  emissions = activity_data × emission_factor
  total = scope1 + scope2 + scope3
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.sustainability import (
    EMISSION_SCOPES,
    INVENTORY_STATUSES,
    CarbonInventoryModel,
    EmissionSourceModel,
)

from .objective_service import SustainabilityError, SustainabilityConflict, _assert_org, _now

# Audit observability counter name
_RECALC_COUNTER = "carbon_inventory_recalculations_total"


def calculate_emissions(activity_data: float, emission_factor: float) -> float:
    """Deterministic formula: emissions = activity_data × emission_factor."""
    return round(activity_data * emission_factor, 6)


def add_emission_source(
    organization_id: str,
    name: str,
    scope: str,
    activity_data: float,
    emission_factor: float,
    period_start: datetime,
    period_end: datetime,
    reporting_year: int,
    actor_id: str,
    session: Session,
    *,
    category: str | None = None,
    activity_unit: str | None = None,
    emission_factor_unit: str | None = None,
    source_reference: str | None = None,
    inventory_id: str | None = None,
) -> EmissionSourceModel:
    if scope not in EMISSION_SCOPES:
        raise SustainabilityError(f"Invalid scope: {scope}")
    calculated = calculate_emissions(activity_data, emission_factor)
    now = _now()
    src = EmissionSourceModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        scope=scope,
        category=category,
        activity_data=activity_data,
        activity_unit=activity_unit,
        emission_factor=emission_factor,
        emission_factor_unit=emission_factor_unit,
        calculated_emissions=calculated,
        period_start=period_start,
        period_end=period_end,
        reporting_year=reporting_year,
        source_reference=source_reference,
        inventory_id=inventory_id,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(src)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.emission_source.added",
        actor_id=actor_id,
        resource_type="emission_source",
        resource_id=src.id,
        details={
            "scope": scope,
            "activity_data": activity_data,
            "emission_factor": emission_factor,
            "calculated_emissions": calculated,
        },
    )
    return src


def list_emission_sources(
    organization_id: str,
    session: Session,
    *,
    reporting_year: int | None = None,
    scope: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EmissionSourceModel]:
    q = session.query(EmissionSourceModel).filter(
        EmissionSourceModel.organization_id == organization_id
    )
    if reporting_year:
        q = q.filter(EmissionSourceModel.reporting_year == reporting_year)
    if scope:
        q = q.filter(EmissionSourceModel.scope == scope)
    return q.order_by(EmissionSourceModel.period_start.desc()).limit(limit).offset(offset).all()


def create_or_get_inventory(
    organization_id: str,
    reporting_year: int,
    period_start: datetime,
    period_end: datetime,
    actor_id: str,
    session: Session,
) -> CarbonInventoryModel:
    existing = (
        session.query(CarbonInventoryModel)
        .filter(
            CarbonInventoryModel.organization_id == organization_id,
            CarbonInventoryModel.reporting_year == reporting_year,
        )
        .first()
    )
    if existing:
        return existing
    now = _now()
    inv = CarbonInventoryModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        reporting_year=reporting_year,
        period_start=period_start,
        period_end=period_end,
        total_emissions=0.0,
        scope1_emissions=0.0,
        scope2_emissions=0.0,
        scope3_emissions=0.0,
        unit="tCO2e",
        inventory_status="DRAFT",
        recalculation_count=0,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(inv)
    session.flush()
    return inv


def recalculate_inventory(
    inventory_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> CarbonInventoryModel:
    """Aggregate emission sources into inventory. Deterministic and auditable."""
    inv = session.get(CarbonInventoryModel, inventory_id)
    _assert_org(inv, organization_id, "Carbon inventory")
    if inv.inventory_status == "FINALIZED":
        raise SustainabilityConflict("Finalized inventory cannot be recalculated")

    # Sum emissions by scope for this reporting year
    def _sum_scope(scope: str) -> float:
        row = (
            session.query(func.sum(EmissionSourceModel.calculated_emissions))
            .filter(
                EmissionSourceModel.organization_id == organization_id,
                EmissionSourceModel.reporting_year == inv.reporting_year,
                EmissionSourceModel.scope == scope,
            )
            .scalar()
        )
        return round(float(row or 0.0), 6)

    s1 = _sum_scope("SCOPE1")
    s2 = _sum_scope("SCOPE2")
    s3 = _sum_scope("SCOPE3")
    total = round(s1 + s2 + s3, 6)

    inv.scope1_emissions = s1
    inv.scope2_emissions = s2
    inv.scope3_emissions = s3
    inv.total_emissions = total
    inv.last_calculated_at = _now()
    inv.recalculation_count += 1
    inv.updated_by = actor_id
    inv.updated_at = _now()
    session.flush()

    emit_audit_event(
        session=session,
        event_type="sustainability.carbon_inventory.recalculated",
        actor_id=actor_id,
        resource_type="carbon_inventory",
        resource_id=inventory_id,
        details={
            "scope1": s1,
            "scope2": s2,
            "scope3": s3,
            "total": total,
            "recalculation_count": inv.recalculation_count,
        },
    )
    sustainability_counters.record_inventory_recalculated()
    return inv


def finalize_inventory(
    inventory_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> CarbonInventoryModel:
    inv = session.get(CarbonInventoryModel, inventory_id)
    _assert_org(inv, organization_id, "Carbon inventory")
    if inv.inventory_status == "FINALIZED":
        raise SustainabilityConflict("Inventory is already finalized")
    inv.inventory_status = "FINALIZED"
    inv.updated_by = actor_id
    inv.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.carbon_inventory.finalized",
        actor_id=actor_id,
        resource_type="carbon_inventory",
        resource_id=inventory_id,
        details={"total_emissions": inv.total_emissions, "unit": inv.unit},
    )
    sustainability_counters.record_inventory_finalized()
    return inv


def get_inventory(inventory_id: str, session: Session) -> CarbonInventoryModel | None:
    return session.get(CarbonInventoryModel, inventory_id)


def list_inventories(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[CarbonInventoryModel]:
    return (
        session.query(CarbonInventoryModel)
        .filter(CarbonInventoryModel.organization_id == organization_id)
        .order_by(CarbonInventoryModel.reporting_year.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
