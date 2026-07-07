"""M43 — Financial ESG KPI Framework and Measurements."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    FINANCIAL_KPI_CATEGORIES,
    FINANCIAL_KPI_FREQUENCIES,
    FinancialESGKPIModel,
    FinancialKPIMeasurementModel,
)


class FinancialESGError(Exception):
    pass


class FinancialESGConflict(FinancialESGError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise FinancialESGError(f"{label} not found")


def create_kpi(
    organization_id: str,
    name: str,
    category: str,
    actor_id: str,
    session: Session,
    *,
    formula: str | None = None,
    unit: str | None = None,
    frequency: str = "QUARTERLY",
    owner_user_id: str | None = None,
    description: str | None = None,
) -> FinancialESGKPIModel:
    if category not in FINANCIAL_KPI_CATEGORIES:
        raise FinancialESGError(f"Invalid category: {category}")
    if frequency not in FINANCIAL_KPI_FREQUENCIES:
        raise FinancialESGError(f"Invalid frequency: {frequency}")
    now = _now()
    kpi = FinancialESGKPIModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        category=category,
        formula=formula,
        unit=unit,
        frequency=frequency,
        owner_user_id=owner_user_id,
        description=description,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(kpi)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.kpi.created",
        actor_id=actor_id,
        resource_type="financial_esg_kpi",
        resource_id=kpi.id,
        details={"name": name, "category": category, "frequency": frequency},
    )
    financial_esg_counters.record_kpi_created()
    return kpi


def list_kpis(
    organization_id: str,
    session: Session,
    *,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[FinancialESGKPIModel]:
    q = session.query(FinancialESGKPIModel).filter(
        FinancialESGKPIModel.organization_id == organization_id
    )
    if category:
        q = q.filter(FinancialESGKPIModel.category == category)
    return q.order_by(FinancialESGKPIModel.name).limit(limit).offset(offset).all()


def record_measurement(
    kpi_id: str,
    organization_id: str,
    period: str,
    value: float,
    actor_id: str,
    session: Session,
    *,
    source: str | None = None,
    confidence: float | None = None,
    notes: str | None = None,
) -> FinancialKPIMeasurementModel:
    kpi = session.get(FinancialESGKPIModel, kpi_id)
    if kpi is None or kpi.organization_id != organization_id:
        raise FinancialESGError("Financial KPI not found")
    now = _now()
    m = FinancialKPIMeasurementModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        kpi_id=kpi_id,
        period=period,
        value=value,
        source=source,
        confidence=confidence,
        notes=notes,
        calculated_at=now,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(m)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.kpi.measured",
        actor_id=actor_id,
        resource_type="financial_kpi_measurement",
        resource_id=m.id,
        details={"kpi_id": kpi_id, "period": period, "value": value},
    )
    financial_esg_counters.record_measurement_recorded()
    return m


def list_measurements(
    kpi_id: str,
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[FinancialKPIMeasurementModel]:
    kpi = session.get(FinancialESGKPIModel, kpi_id)
    if kpi is None or kpi.organization_id != organization_id:
        raise FinancialESGError("Financial KPI not found")
    return (
        session.query(FinancialKPIMeasurementModel)
        .filter(FinancialKPIMeasurementModel.kpi_id == kpi_id)
        .order_by(FinancialKPIMeasurementModel.period.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
