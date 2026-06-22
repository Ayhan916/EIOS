"""M44 — Enterprise Digital Twin service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import (
    SNAPSHOT_TYPES,
    DigitalTwinSnapshotModel,
    EnterpriseDigitalTwinModel,
)


class StrategyError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def create_digital_twin(
    organization_id: str,
    name: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    twin_version: str = "1.0.0",
    snapshot_date: datetime | None = None,
    business_units: dict | None = None,
    legal_entities: dict | None = None,
    regions: dict | None = None,
    supplier_count: int = 0,
    esg_programs: dict | None = None,
    kpi_count: int = 0,
    risk_count: int = 0,
    emissions_baseline_tco2e: float | None = None,
    financial_baseline: dict | None = None,
    assumptions: dict | None = None,
    model_config_data: dict | None = None,
) -> EnterpriseDigitalTwinModel:
    now = _now()
    twin = EnterpriseDigitalTwinModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        description=description,
        twin_version=twin_version,
        snapshot_date=snapshot_date or now,
        business_units=business_units,
        legal_entities=legal_entities,
        regions=regions,
        supplier_count=supplier_count,
        esg_programs=esg_programs,
        kpi_count=kpi_count,
        risk_count=risk_count,
        emissions_baseline_tco2e=emissions_baseline_tco2e,
        financial_baseline=financial_baseline,
        assumptions=assumptions,
        model_config_data=model_config_data,
        is_active=True,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(twin)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.digital_twin.created",
        actor_id=actor_id,
        resource_type="enterprise_digital_twin",
        resource_id=twin.id,
        details={"name": name, "twin_version": twin_version},
    )
    strategy_counters.record_digital_twin()
    return twin


def create_snapshot(
    organization_id: str,
    twin_id: str,
    snapshot_type: str,
    snapshot_period: str,
    actor_id: str,
    session: Session,
    *,
    sustainability_state: dict | None = None,
    financial_esg_state: dict | None = None,
    hierarchy_state: dict | None = None,
    climate_risk_state: dict | None = None,
) -> DigitalTwinSnapshotModel:
    if snapshot_type not in SNAPSHOT_TYPES:
        raise StrategyError(f"Invalid snapshot_type: {snapshot_type}")
    twin = session.get(EnterpriseDigitalTwinModel, twin_id)
    _assert_org(twin, organization_id, "digital twin")
    now = _now()
    snap = DigitalTwinSnapshotModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        twin_id=twin_id,
        snapshot_type=snapshot_type,
        snapshot_period=snapshot_period,
        sustainability_state=sustainability_state,
        financial_esg_state=financial_esg_state,
        hierarchy_state=hierarchy_state,
        climate_risk_state=climate_risk_state,
        captured_at=now,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(snap)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.snapshot.created",
        actor_id=actor_id,
        resource_type="digital_twin_snapshot",
        resource_id=snap.id,
        details={"twin_id": twin_id, "snapshot_type": snapshot_type, "snapshot_period": snapshot_period},
    )
    strategy_counters.record_snapshot()
    return snap


def list_digital_twins(organization_id: str, session: Session) -> list[EnterpriseDigitalTwinModel]:
    return (
        session.query(EnterpriseDigitalTwinModel)
        .filter(EnterpriseDigitalTwinModel.organization_id == organization_id)
        .order_by(EnterpriseDigitalTwinModel.created_at.desc())
        .all()
    )


def list_snapshots(
    organization_id: str,
    twin_id: str,
    session: Session,
) -> list[DigitalTwinSnapshotModel]:
    twin = session.get(EnterpriseDigitalTwinModel, twin_id)
    _assert_org(twin, organization_id, "digital twin")
    return (
        session.query(DigitalTwinSnapshotModel)
        .filter(
            DigitalTwinSnapshotModel.organization_id == organization_id,
            DigitalTwinSnapshotModel.twin_id == twin_id,
        )
        .order_by(DigitalTwinSnapshotModel.captured_at.desc())
        .all()
    )
