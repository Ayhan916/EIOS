"""AI Model Monitoring — snapshots, drift detection, and policy enforcement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.ai_governance import (
    AI_POLICY_TYPES,
    DRIFT_ALERT_TYPES,
    RISK_LEVELS,
    AIModelModel,
    AIPolicyModel,
    ModelDriftAlertModel,
    ModelMonitoringRecordModel,
)

from .inventory_service import AIGovernanceError

# Drift thresholds. Stored as module-level constants so they are auditable
# via code review and grep. A future migration should move these to a
# per-model configuration table.
_DRIFT_AUTO_ALERT_THRESHOLD: float = 0.3
_DRIFT_HIGH_SEVERITY_THRESHOLD: float = 0.6


def _now() -> datetime:
    return datetime.now(UTC)


def record_monitoring_snapshot(
    model_id: str,
    organization_id: str,
    period_start: datetime,
    period_end: datetime,
    actor_id: str,
    session: Session,
    *,
    avg_latency_ms: float | None = None,
    failure_count: int = 0,
    usage_count: int = 0,
    avg_confidence: float | None = None,
    drift_score: float | None = None,
    notes: str | None = None,
) -> ModelMonitoringRecordModel:
    rec = ModelMonitoringRecordModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        organization_id=organization_id,
        period_start=period_start,
        period_end=period_end,
        avg_latency_ms=avg_latency_ms,
        failure_count=failure_count,
        usage_count=usage_count,
        avg_confidence=avg_confidence,
        drift_score=drift_score,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(rec)
    session.flush()

    if drift_score is not None and drift_score >= _DRIFT_AUTO_ALERT_THRESHOLD:
        severity = "HIGH" if drift_score >= _DRIFT_HIGH_SEVERITY_THRESHOLD else "MEDIUM"
        create_drift_alert(
            model_id=model_id,
            alert_type="DISTRIBUTION_SHIFT",
            severity=severity,
            description=f"Drift score {drift_score:.3f} exceeded threshold {_DRIFT_AUTO_ALERT_THRESHOLD}",
            actor_id=actor_id,
            session=session,
        )

    return rec


def create_drift_alert(
    model_id: str,
    alert_type: str,
    severity: str,
    description: str,
    actor_id: str,
    session: Session,
    *,
    detected_at: datetime | None = None,
) -> ModelDriftAlertModel:
    if alert_type not in DRIFT_ALERT_TYPES:
        raise AIGovernanceError(f"Invalid alert_type: {alert_type}")
    if severity not in RISK_LEVELS:
        raise AIGovernanceError(f"Invalid severity: {severity}")

    alert = ModelDriftAlertModel(
        id=str(uuid.uuid4()),
        model_id=model_id,
        alert_type=alert_type,
        severity=severity,
        description=description,
        detected_at=detected_at or _now(),
        is_resolved=False,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(alert)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.drift_alert.created",
        actor_id=actor_id,
        resource_type="model_drift_alert",
        resource_id=alert.id,
        details={"model_id": model_id, "alert_type": alert_type, "severity": severity},
    )
    return alert


def resolve_drift_alert(
    alert_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> ModelDriftAlertModel:
    alert = session.get(ModelDriftAlertModel, alert_id)
    if not alert:
        raise AIGovernanceError(f"Drift alert {alert_id} not found")

    # Verify the alert's model belongs to this organization
    model = session.get(AIModelModel, alert.model_id)
    if not model or model.organization_id != organization_id:
        raise AIGovernanceError(f"Drift alert {alert_id} not found")

    alert.is_resolved = True
    alert.resolved_at = _now()
    alert.updated_by = actor_id
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.drift_alert.resolved",
        actor_id=actor_id,
        resource_type="model_drift_alert",
        resource_id=alert_id,
        details={"model_id": alert.model_id},
    )
    return alert


def list_drift_alerts(
    model_id: str,
    session: Session,
    *,
    unresolved_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ModelDriftAlertModel]:
    q = session.query(ModelDriftAlertModel).filter(ModelDriftAlertModel.model_id == model_id)
    if unresolved_only:
        q = q.filter(ModelDriftAlertModel.is_resolved == False)  # noqa: E712
    return q.order_by(ModelDriftAlertModel.detected_at.desc()).limit(limit).offset(offset).all()


# ── AI Policies ───────────────────────────────────────────────────────────────


def create_ai_policy(
    name: str,
    policy_type: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str | None = None,
    enterprise_id: str | None = None,
    description: str | None = None,
    policy_body: dict | None = None,
) -> AIPolicyModel:
    if policy_type not in AI_POLICY_TYPES:
        raise AIGovernanceError(f"Invalid policy_type: {policy_type}")

    policy = AIPolicyModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        enterprise_id=enterprise_id,
        name=name,
        policy_type=policy_type,
        description=description,
        policy_body=policy_body or {},
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(policy)
    session.flush()

    emit_audit_event(
        session=session,
        event_type="ai.policy.created",
        actor_id=actor_id,
        resource_type="ai_policy",
        resource_id=policy.id,
        details={"name": name, "policy_type": policy_type},
    )
    return policy


def list_ai_policies(
    session: Session,
    *,
    organization_id: str | None = None,
    enterprise_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AIPolicyModel]:
    q = session.query(AIPolicyModel).filter(AIPolicyModel.is_active == True)  # noqa: E712
    if organization_id:
        q = q.filter(AIPolicyModel.organization_id == organization_id)
    if enterprise_id:
        q = q.filter(AIPolicyModel.enterprise_id == enterprise_id)
    return q.limit(limit).offset(offset).all()
