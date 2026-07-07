"""M36 Alert Engine and Escalation Service.

AlertEngine.evaluate()  — run escalation rules against an AgentFinding, create alerts
AlertEngine.create_alert()  — directly create an alert (bypassing rules)

Escalation Rules:
  condition_json defines what triggers escalation. Supported metrics:
    risk_score_delta     — float, operator: lt/gt
    esg_score            — float, operator: lt/gt
    sanctions_exposure   — bool
    overdue_days         — int, operator: gt
    severity             — string match
    confidence_score     — float, operator: gt/lt
    category             — string match

Built-in automatic escalation (no rule needed):
    CRITICAL severity findings → CRITICAL alert
    HIGH severity + confidence >= 0.8 → HIGH alert
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
    """Write a governance action to AuditEventModel.  Non-fatal — failures never
    abort the caller's transaction."""
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


# Built-in escalation thresholds (applied before user-defined rules)
_AUTO_ESCALATION: list[dict] = [
    {"severity": "CRITICAL", "alert_severity": "CRITICAL"},
    {"severity": "HIGH", "min_confidence": 0.75, "alert_severity": "HIGH"},
    {"severity": "MEDIUM", "min_confidence": 0.9, "alert_severity": "WARNING"},
]


async def _find_open_alert_duplicate(
    organization_id: str,
    supplier_id: str | None,
    agent_finding_id: str | None,
    severity: str,
    title: str,
    session,
) -> object | None:
    """Return an existing unacknowledged alert for the same finding+severity, or None.

    When agent_finding_id is set, dedupe on (org, finding_id, severity).
    When not set (direct alert), dedupe on (org, supplier_id, severity, title[:100]).
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel

    if agent_finding_id:
        stmt = (
            select(AgentAlertModel)
            .where(
                AgentAlertModel.organization_id == organization_id,
                AgentAlertModel.agent_finding_id == agent_finding_id,
                AgentAlertModel.severity == severity.upper(),
                AgentAlertModel.acknowledged_at.is_(None),
            )
            .limit(1)
        )
    else:
        stmt = (
            select(AgentAlertModel)
            .where(
                AgentAlertModel.organization_id == organization_id,
                AgentAlertModel.supplier_id == supplier_id,
                AgentAlertModel.severity == severity.upper(),
                AgentAlertModel.title == title[:500],
                AgentAlertModel.acknowledged_at.is_(None),
            )
            .limit(1)
        )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_alert(
    organization_id: str,
    agent_id: str,
    severity: str,
    title: str,
    message: str,
    supplier_id: str | None = None,
    agent_finding_id: str | None = None,
    skip_if_open: bool = True,
    session=None,
) -> object:
    """Create a single alert record. Deduplicates open alerts by default.

    skip_if_open: if True (default) and an unacknowledged alert for the same
    finding+severity already exists, return the existing alert instead of
    creating a duplicate.
    """
    from application.agent_monitoring.metrics import agent_counters
    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel

    if skip_if_open:
        existing = await _find_open_alert_duplicate(
            organization_id, supplier_id, agent_finding_id, severity, title, session
        )
        if existing is not None:
            return existing

    now = datetime.now(UTC)
    alert = AgentAlertModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        supplier_id=supplier_id,
        agent_id=agent_id,
        agent_finding_id=agent_finding_id,
        severity=severity.upper(),
        title=title,
        message=message,
        acknowledged_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    await session.flush()

    # Metrics
    agent_counters.record_alert_created()

    # Audit: alert escalated for HIGH/CRITICAL (governance-relevant)
    if alert.severity in ("HIGH", "CRITICAL"):
        await _log_audit_event(
            session=session,
            action="agent.alert.escalated",
            actor_id=agent_id,
            entity_type="AgentAlert",
            entity_id=alert.id,
            detail=f"Alert escalated: {title[:100]}",
            metadata={
                "organization_id": organization_id,
                "severity": alert.severity,
                "agent_finding_id": agent_finding_id,
            },
        )

    return alert


async def evaluate_finding(
    finding,
    organization_id: str,
    session,
    agent_type: str = "*",
) -> list:
    """Run automatic escalation and org-specific rules against a finding.

    F5: agent_type filters user-defined escalation rules so that a rule
    scoped to "RISK_MONITOR" does not fire for INTELLIGENCE_MONITOR findings.
    Rules with agent_type="*" apply to all agents.

    Returns list of created AgentAlertModel records.
    """
    from sqlalchemy import or_, select

    from infrastructure.persistence.models.agent_monitoring import EscalationRuleModel

    created_alerts = []

    # Automatic built-in escalation
    for rule in _AUTO_ESCALATION:
        if finding.severity != rule["severity"]:
            continue
        min_conf = rule.get("min_confidence", 0.0)
        if finding.confidence_score < min_conf:
            continue
        alert = await create_alert(
            organization_id=organization_id,
            agent_id=finding.agent_id,
            severity=rule["alert_severity"],
            title=f"[Auto] {finding.title}",
            message=finding.description,
            supplier_id=finding.supplier_id,
            agent_finding_id=finding.id,
            session=session,
        )
        created_alerts.append(alert)
        # Only one auto-escalation per finding
        break

    # F5: User-defined escalation rules — filtered by agent_type
    rule_stmt = select(EscalationRuleModel).where(
        EscalationRuleModel.organization_id == organization_id,
        EscalationRuleModel.enabled.is_(True),
        or_(
            EscalationRuleModel.agent_type == "*",
            EscalationRuleModel.agent_type == agent_type,
        ),
    )
    rules = list((await session.execute(rule_stmt)).scalars().all())

    for rule in rules:
        if _matches_rule(finding, rule.condition_json):
            alert = await create_alert(
                organization_id=organization_id,
                agent_id=finding.agent_id,
                severity=rule.escalation_severity,
                title=f"[{rule.name}] {finding.title}",
                message=f"Escalation rule '{rule.name}' triggered.\n\n{finding.description}",
                supplier_id=finding.supplier_id,
                agent_finding_id=finding.id,
                session=session,
            )
            created_alerts.append(alert)

    # Trigger notification for HIGH/CRITICAL alerts
    for alert in created_alerts:
        if alert.severity in ("HIGH", "CRITICAL"):
            await _trigger_notification(alert, organization_id, session)

    return created_alerts


def _matches_rule(finding, condition: dict) -> bool:
    """Evaluate a single escalation rule condition against a finding."""
    metric = condition.get("metric", "")
    source = finding.source_data_json if hasattr(finding, "source_data_json") else {}

    if metric == "severity":
        return finding.severity == condition.get("value", "")

    if metric == "confidence_score":
        val = finding.confidence_score
        return _compare(val, condition.get("operator", "gt"), condition.get("threshold", 0.0))

    if metric == "category":
        return finding.category == condition.get("value", "")

    if metric == "sanctions_exposure":
        return bool(source.get("sanctions_exposure", False))

    if metric in ("risk_score_delta", "overdue_days", "esg_score"):
        val = source.get(metric)
        if val is None:
            return False
        return _compare(float(val), condition.get("operator", "lt"), condition.get("threshold", 0))

    return False


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "lt":
        return value < threshold
    if operator == "gt":
        return value > threshold
    if operator == "lte":
        return value <= threshold
    if operator == "gte":
        return value >= threshold
    if operator == "eq":
        return value == threshold
    return False


async def _trigger_notification(alert, organization_id: str, session) -> None:
    """Wire into M24 notification system.  Non-fatal if unavailable."""
    try:
        from application.notification_service import create_notification

        await create_notification(
            organization_id=organization_id,
            title=f"ESG Alert: {alert.title}",
            message=alert.message,
            notification_type="agent_alert",
            severity=alert.severity,
            entity_type="agent_alert",
            entity_id=alert.id,
            session=session,
        )
    except Exception as exc:
        logger.warning("alert_notification_failed", alert_id=alert.id, error=str(exc))


async def acknowledge_alert(
    alert_id: str,
    organization_id: str,
    acknowledged_by: str,
    session,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel

    stmt = select(AgentAlertModel).where(
        AgentAlertModel.id == alert_id,
        AgentAlertModel.organization_id == organization_id,
    )
    alert = (await session.execute(stmt)).scalar_one_or_none()
    if alert is None:
        raise ValueError("Alert not found")
    if alert.acknowledged_at is not None:
        raise ValueError("Alert already acknowledged")

    now = datetime.now(UTC)
    alert.acknowledged_at = now
    alert.acknowledged_by = acknowledged_by
    alert.updated_at = now
    await session.flush()
    return alert


async def list_alerts(
    organization_id: str,
    supplier_id: str | None = None,
    severity: str | None = None,
    unacknowledged_only: bool = False,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel

    stmt = select(AgentAlertModel).where(AgentAlertModel.organization_id == organization_id)
    if supplier_id:
        stmt = stmt.where(AgentAlertModel.supplier_id == supplier_id)
    if severity:
        stmt = stmt.where(AgentAlertModel.severity == severity.upper())
    if unacknowledged_only:
        stmt = stmt.where(AgentAlertModel.acknowledged_at.is_(None))
    stmt = stmt.order_by(AgentAlertModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def create_escalation_rule(
    organization_id: str,
    name: str,
    description: str,
    condition_json: dict,
    escalation_severity: str,
    created_by: str,
    agent_type: str = "*",
    session=None,
) -> object:
    from infrastructure.persistence.models.agent_monitoring import EscalationRuleModel

    now = datetime.now(UTC)
    rule = EscalationRuleModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        description=description,
        agent_type=agent_type,
        condition_json=condition_json,
        escalation_severity=escalation_severity.upper(),
        enabled=True,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    await session.flush()
    return rule


async def list_escalation_rules(
    organization_id: str,
    session,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import EscalationRuleModel

    stmt = (
        select(EscalationRuleModel)
        .where(EscalationRuleModel.organization_id == organization_id)
        .order_by(EscalationRuleModel.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def create_recommendation_draft(
    organization_id: str,
    agent_id: str,
    recommendation_text: str,
    rationale: str,
    confidence_score: float,
    supplier_id: str | None = None,
    agent_finding_id: str | None = None,
    session=None,
) -> object:
    """Create a draft recommendation awaiting human approval.

    Human approval model: agents may ONLY create PENDING drafts.
    Only humans may approve or reject via approve_draft() / reject_draft().
    """
    from application.agent_monitoring.metrics import agent_counters
    from infrastructure.persistence.models.agent_monitoring import RecommendationDraftModel

    now = datetime.now(UTC)
    draft = RecommendationDraftModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        supplier_id=supplier_id,
        agent_id=agent_id,
        agent_finding_id=agent_finding_id,
        recommendation_text=recommendation_text,
        rationale=rationale,
        confidence_score=confidence_score,
        draft_status="PENDING",
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(draft)
    await session.flush()
    agent_counters.record_draft_created()
    return draft


async def approve_draft(
    draft_id: str,
    organization_id: str,
    approved_by: str,
    session,
) -> object:
    """Human approves a draft — creates a real Recommendation record.

    Human approval model: this is the only path to a real Recommendation.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import RecommendationDraftModel

    stmt = select(RecommendationDraftModel).where(
        RecommendationDraftModel.id == draft_id,
        RecommendationDraftModel.organization_id == organization_id,
    )
    draft = (await session.execute(stmt)).scalar_one_or_none()
    if draft is None:
        raise ValueError("Draft not found")
    if draft.draft_status != "PENDING":
        raise ValueError(f"Cannot approve draft in status: {draft.draft_status}")

    now = datetime.now(UTC)
    draft.draft_status = "APPROVED"
    draft.approved_by = approved_by
    draft.approved_at = now
    draft.updated_at = now
    await session.flush()

    # Mark the finding as CONVERTED
    if draft.agent_finding_id:
        from application.agent_monitoring.finding_service import mark_converted

        await mark_converted(draft.agent_finding_id, organization_id, session)

    # F7: governance audit trail
    await _log_audit_event(
        session=session,
        action="agent.draft.approved",
        actor_id=approved_by,
        entity_type="RecommendationDraft",
        entity_id=draft_id,
        detail=f"Recommendation draft {draft_id} approved",
        metadata={"organization_id": organization_id, "agent_finding_id": draft.agent_finding_id},
    )

    logger.info("recommendation_draft_approved", draft_id=draft_id, approved_by=approved_by)
    return draft


async def reject_draft(
    draft_id: str,
    organization_id: str,
    rejected_by: str,
    reason: str,
    session,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import RecommendationDraftModel

    stmt = select(RecommendationDraftModel).where(
        RecommendationDraftModel.id == draft_id,
        RecommendationDraftModel.organization_id == organization_id,
    )
    draft = (await session.execute(stmt)).scalar_one_or_none()
    if draft is None:
        raise ValueError("Draft not found")
    if draft.draft_status != "PENDING":
        raise ValueError(f"Cannot reject draft in status: {draft.draft_status}")

    now = datetime.now(UTC)
    draft.draft_status = "REJECTED"
    draft.approved_by = rejected_by
    draft.approved_at = now
    draft.rejection_reason = reason
    draft.updated_at = now
    await session.flush()

    # F7: governance audit trail
    await _log_audit_event(
        session=session,
        action="agent.draft.rejected",
        actor_id=rejected_by,
        entity_type="RecommendationDraft",
        entity_id=draft_id,
        detail=f"Recommendation draft {draft_id} rejected: {reason}",
        metadata={"organization_id": organization_id, "reason": reason},
    )

    return draft


async def list_recommendation_drafts(
    organization_id: str,
    draft_status: str | None = None,
    supplier_id: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import RecommendationDraftModel

    stmt = select(RecommendationDraftModel).where(
        RecommendationDraftModel.organization_id == organization_id
    )
    if draft_status:
        stmt = stmt.where(RecommendationDraftModel.draft_status == draft_status.upper())
    if supplier_id:
        stmt = stmt.where(RecommendationDraftModel.supplier_id == supplier_id)
    stmt = stmt.order_by(RecommendationDraftModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
