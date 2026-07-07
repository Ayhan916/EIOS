"""KPI Management — definitions, measurements, and alerts."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.sustainability import (
    ALERT_TYPES,
    KPI_CATEGORIES,
    MEASUREMENT_FREQUENCIES,
    ESGKPIModel,
    KPIAlertModel,
    KPIMeasurementModel,
)

from .objective_service import SustainabilityError, _assert_org, _now


def create_kpi(
    organization_id: str,
    name: str,
    category: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    formula: str | None = None,
    unit: str | None = None,
    frequency: str = "QUARTERLY",
    target_value: float | None = None,
    alert_threshold: float | None = None,
) -> ESGKPIModel:
    if category not in KPI_CATEGORIES:
        raise SustainabilityError(f"Invalid KPI category: {category}")
    if frequency not in MEASUREMENT_FREQUENCIES:
        raise SustainabilityError(f"Invalid frequency: {frequency}")
    now = _now()
    kpi = ESGKPIModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        category=category,
        description=description,
        formula=formula,
        unit=unit,
        frequency=frequency,
        is_active=True,
        target_value=target_value,
        alert_threshold=alert_threshold,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(kpi)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.kpi.created",
        actor_id=actor_id,
        resource_type="esg_kpi",
        resource_id=kpi.id,
        details={"name": name, "category": category},
    )
    sustainability_counters.record_kpi_created()
    return kpi


def get_kpi(kpi_id: str, session: Session) -> ESGKPIModel | None:
    return session.get(ESGKPIModel, kpi_id)


def list_kpis(
    organization_id: str,
    session: Session,
    *,
    category: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ESGKPIModel]:
    q = session.query(ESGKPIModel).filter(ESGKPIModel.organization_id == organization_id)
    if category:
        q = q.filter(ESGKPIModel.category == category)
    if active_only:
        q = q.filter(ESGKPIModel.is_active == True)  # noqa: E712
    return q.order_by(ESGKPIModel.name).limit(limit).offset(offset).all()


def record_measurement(
    kpi_id: str,
    organization_id: str,
    period_start: datetime,
    period_end: datetime,
    measured_value: float,
    actor_id: str,
    session: Session,
    *,
    source: str | None = None,
    confidence: float | None = None,
    notes: str | None = None,
) -> KPIMeasurementModel:
    kpi = session.get(ESGKPIModel, kpi_id)
    if kpi is None or kpi.organization_id != organization_id:
        raise SustainabilityError("KPI not found")
    now = _now()
    m = KPIMeasurementModel(
        id=str(uuid.uuid4()),
        kpi_id=kpi_id,
        organization_id=organization_id,
        period_start=period_start,
        period_end=period_end,
        measured_value=measured_value,
        source=source,
        confidence=confidence,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(m)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.kpi.measured",
        actor_id=actor_id,
        resource_type="kpi_measurement",
        resource_id=m.id,
        details={"kpi_id": kpi_id, "measured_value": measured_value},
    )
    sustainability_counters.record_measurement_recorded()
    # Auto-check threshold alert
    if kpi.alert_threshold is not None and measured_value > kpi.alert_threshold:
        _create_alert(
            kpi_id=kpi_id,
            organization_id=organization_id,
            alert_type="THRESHOLD_BREACH",
            triggered_value=measured_value,
            threshold_value=kpi.alert_threshold,
            actor_id=actor_id,
            session=session,
        )
    return m


def list_measurements(
    kpi_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[KPIMeasurementModel]:
    return (
        session.query(KPIMeasurementModel)
        .filter(KPIMeasurementModel.kpi_id == kpi_id)
        .order_by(KPIMeasurementModel.period_start.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def _create_alert(
    kpi_id: str,
    organization_id: str,
    alert_type: str,
    triggered_value: float,
    actor_id: str,
    session: Session,
    *,
    threshold_value: float | None = None,
    message: str | None = None,
) -> KPIAlertModel:
    if alert_type not in ALERT_TYPES:
        raise SustainabilityError(f"Invalid alert_type: {alert_type}")
    now = _now()
    alert_message = message or (
        f"{alert_type}: triggered_value={triggered_value}"
        + (f", threshold={threshold_value}" if threshold_value is not None else "")
    )
    alert = KPIAlertModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        kpi_id=kpi_id,
        alert_type=alert_type,
        threshold_value=threshold_value,
        triggered_value=triggered_value,
        message=alert_message,
        is_resolved=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    session.flush()
    sustainability_counters.record_kpi_alert()
    return alert


def create_kpi_alert(
    kpi_id: str,
    organization_id: str,
    alert_type: str,
    triggered_value: float,
    actor_id: str,
    session: Session,
    *,
    threshold_value: float | None = None,
    message: str | None = None,
) -> KPIAlertModel:
    return _create_alert(
        kpi_id=kpi_id,
        organization_id=organization_id,
        alert_type=alert_type,
        triggered_value=triggered_value,
        actor_id=actor_id,
        session=session,
        threshold_value=threshold_value,
        message=message,
    )


def resolve_alert(
    alert_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> KPIAlertModel:
    alert = session.get(KPIAlertModel, alert_id)
    _assert_org(alert, organization_id, "KPI alert")
    if alert.is_resolved:
        raise SustainabilityError("Alert is already resolved")
    alert.is_resolved = True
    alert.resolved_at = _now()
    alert.resolved_by = actor_id
    alert.updated_by = actor_id
    alert.updated_at = _now()
    session.flush()
    return alert


def list_alerts(
    organization_id: str,
    session: Session,
    *,
    kpi_id: str | None = None,
    unresolved_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[KPIAlertModel]:
    q = session.query(KPIAlertModel).filter(KPIAlertModel.organization_id == organization_id)
    if kpi_id:
        q = q.filter(KPIAlertModel.kpi_id == kpi_id)
    if unresolved_only:
        q = q.filter(KPIAlertModel.is_resolved == False)  # noqa: E712
    return q.order_by(KPIAlertModel.created_at.desc()).limit(limit).offset(offset).all()
