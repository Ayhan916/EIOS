"""M36 Agent Finding Service.

Findings are agent-generated recommendations, never authoritative facts.
Humans decide what to do with them.

Human approval model enforced here:
  - Agents may create, list, acknowledge findings.
  - Agents may NOT close risks, approve evidence, close assessments.
  - `convert_to_finding()` creates a PENDING recommendation draft — not an approval.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    detail: str = "",
    metadata: dict | None = None,
) -> None:
    """Write a governance action to AuditEventModel.  Non-fatal."""
    from infrastructure.persistence.models.audit_event import AuditEventModel

    now = datetime.now(UTC)
    try:
        event = AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata=metadata or {},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning(
            "agent_audit_event_failed",
            action=action,
            entity_id=entity_id,
            error=str(exc),
        )


async def find_open_duplicate(
    organization_id: str,
    supplier_id: str | None,
    category: str,
    rule_triggered: str,
    session,
) -> object | None:
    """Return an existing OPEN or ACKNOWLEDGED finding with the same key, or None."""
    from infrastructure.persistence.models.agent_monitoring import AgentFindingModel
    from sqlalchemy import select

    stmt = select(AgentFindingModel).where(
        AgentFindingModel.organization_id == organization_id,
        AgentFindingModel.supplier_id == supplier_id,
        AgentFindingModel.category == category,
        AgentFindingModel.rule_triggered == rule_triggered,
        AgentFindingModel.finding_status.in_(["OPEN", "ACKNOWLEDGED"]),
    ).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_finding(
    organization_id: str,
    agent_id: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    evidence: str,
    rule_triggered: str,
    source_data: dict,
    confidence_score: float = 0.8,
    supplier_id: str | None = None,
    agent_run_id: str | None = None,
    skip_if_open: bool = False,
    session=None,
) -> object:
    """Create a new agent finding. Append-only; findings are never deleted.

    skip_if_open: if True and an OPEN/ACKNOWLEDGED finding with the same
    (org, supplier, category, rule_triggered) already exists, return it instead
    of creating a duplicate.  Used by monitors that run repeatedly.
    """
    from application.agent_monitoring.metrics import agent_counters
    from infrastructure.persistence.models.agent_monitoring import AgentFindingModel

    if skip_if_open:
        existing = await find_open_duplicate(
            organization_id, supplier_id, category, rule_triggered, session
        )
        if existing is not None:
            return existing

    now = datetime.now(UTC)

    # M36.2: Explainability snapshot — capture detection context immutably
    snapshot = {
        **source_data,
        "_snapshot": {
            "rule_triggered": rule_triggered,
            "confidence_score": confidence_score,
            "severity": severity.upper(),
            "detected_at": now.isoformat(),
            "agent_id": agent_id,
        },
    }

    model = AgentFindingModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        supplier_id=supplier_id,
        agent_id=agent_id,
        agent_run_id=agent_run_id,
        category=category,
        severity=severity.upper(),
        title=title,
        description=description,
        evidence=evidence,
        confidence_score=confidence_score,
        detected_at=now,
        finding_status="OPEN",
        rule_triggered=rule_triggered,
        source_data_json=snapshot,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()

    # Metrics
    agent_counters.record_finding_created()

    # Audit: finding created (non-fatal)
    await _log_audit_event(
        session=session,
        action="agent.finding.created",
        actor_id=agent_id,
        entity_type="AgentFinding",
        entity_id=model.id,
        detail=f"Agent finding created: {title[:100]}",
        metadata={
            "organization_id": organization_id,
            "category": category,
            "severity": severity.upper(),
            "rule_triggered": rule_triggered,
        },
    )

    return model


async def list_findings(
    organization_id: str,
    supplier_id: str | None = None,
    agent_id: str | None = None,
    finding_status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session=None,
) -> list:
    from infrastructure.persistence.models.agent_monitoring import AgentFindingModel
    from sqlalchemy import select

    stmt = select(AgentFindingModel).where(
        AgentFindingModel.organization_id == organization_id
    )
    if supplier_id:
        stmt = stmt.where(AgentFindingModel.supplier_id == supplier_id)
    if agent_id:
        stmt = stmt.where(AgentFindingModel.agent_id == agent_id)
    if finding_status:
        stmt = stmt.where(AgentFindingModel.finding_status == finding_status.upper())
    if severity:
        stmt = stmt.where(AgentFindingModel.severity == severity.upper())
    stmt = stmt.order_by(AgentFindingModel.detected_at.desc()).limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


async def get_finding(
    finding_id: str,
    organization_id: str,
    session,
) -> object | None:
    from infrastructure.persistence.models.agent_monitoring import AgentFindingModel
    from sqlalchemy import select

    stmt = select(AgentFindingModel).where(
        AgentFindingModel.id == finding_id,
        AgentFindingModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def acknowledge_finding(
    finding_id: str,
    organization_id: str,
    acknowledged_by: str,
    session,
) -> object:
    """Human acknowledges a finding. Does NOT close/resolve anything."""
    finding = await get_finding(finding_id, organization_id, session)
    if finding is None:
        raise ValueError("Finding not found")
    if finding.finding_status != "OPEN":
        raise ValueError(f"Cannot acknowledge finding in status: {finding.finding_status}")

    now = datetime.now(UTC)
    finding.finding_status = "ACKNOWLEDGED"
    finding.acknowledged_by = acknowledged_by
    finding.acknowledged_at = now
    finding.updated_at = now
    await session.flush()

    # F7: governance audit trail
    await _log_audit_event(
        session=session,
        action="agent.finding.acknowledged",
        actor_id=acknowledged_by,
        entity_type="AgentFinding",
        entity_id=finding_id,
        detail=f"Agent finding {finding_id} acknowledged",
        metadata={"organization_id": organization_id},
    )

    return finding


async def dismiss_finding(
    finding_id: str,
    organization_id: str,
    dismissed_by: str,
    session,
) -> object:
    """Human dismisses a finding as not actionable."""
    finding = await get_finding(finding_id, organization_id, session)
    if finding is None:
        raise ValueError("Finding not found")
    if finding.finding_status not in ("OPEN", "ACKNOWLEDGED"):
        raise ValueError(f"Cannot dismiss finding in status: {finding.finding_status}")

    now = datetime.now(UTC)
    finding.finding_status = "DISMISSED"
    finding.acknowledged_by = dismissed_by
    finding.acknowledged_at = now
    finding.updated_at = now
    await session.flush()

    # F7: governance audit trail
    await _log_audit_event(
        session=session,
        action="agent.finding.dismissed",
        actor_id=dismissed_by,
        entity_type="AgentFinding",
        entity_id=finding_id,
        detail=f"Agent finding {finding_id} dismissed",
        metadata={"organization_id": organization_id},
    )

    return finding


async def mark_converted(
    finding_id: str,
    organization_id: str,
    session,
) -> None:
    """Mark finding as CONVERTED when a draft recommendation is approved."""
    finding = await get_finding(finding_id, organization_id, session)
    if finding is None:
        return

    now = datetime.now(UTC)
    finding.finding_status = "CONVERTED"
    finding.updated_at = now
    await session.flush()
