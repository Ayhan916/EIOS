"""M39 Governance Escalation Service.

Rule-based only. Evaluates GovernanceEscalationRules against live entity state
and surfaces escalation notifications. Humans decide whether to act.

No autonomous action, approval, or closure.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.operating_system.metrics import os_counters


async def create_escalation_rule(
    organization_id: str,
    rule_name: str,
    condition_entity_type: str,
    condition_status: str,
    escalate_to_role: str,
    session: AsyncSession,
    condition_overdue_days: int | None = None,
    condition_priority: str | None = None,
    escalate_to_user_id: str | None = None,
    notification_message: str = "",
) -> dict:
    from infrastructure.persistence.models.operating_system import GovernanceEscalationRuleModel
    now = datetime.now(UTC)
    rule = GovernanceEscalationRuleModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        rule_name=rule_name,
        condition_entity_type=condition_entity_type,
        condition_status=condition_status,
        condition_overdue_days=condition_overdue_days,
        condition_priority=condition_priority,
        escalate_to_role=escalate_to_role,
        escalate_to_user_id=escalate_to_user_id,
        notification_message=notification_message,
        rule_status="ACTIVE",
    )
    session.add(rule)
    await session.flush()
    return _rule_to_dict(rule)


async def list_escalation_rules(
    organization_id: str, session: AsyncSession
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import GovernanceEscalationRuleModel
    stmt = select(GovernanceEscalationRuleModel).where(
        GovernanceEscalationRuleModel.organization_id == organization_id,
        GovernanceEscalationRuleModel.rule_status == "ACTIVE",
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_rule_to_dict(r) for r in rows]


async def evaluate_escalations(
    organization_id: str, session: AsyncSession
) -> list[dict]:
    """Evaluate all ACTIVE escalation rules and return triggered escalations.

    Only surfaces escalations — no autonomous action is taken.
    """
    from infrastructure.persistence.models.operating_system import (
        GovernanceEscalationRuleModel, ESGActionModel,
    )
    rules_stmt = select(GovernanceEscalationRuleModel).where(
        GovernanceEscalationRuleModel.organization_id == organization_id,
        GovernanceEscalationRuleModel.rule_status == "ACTIVE",
    )
    rules = (await session.execute(rules_stmt)).scalars().all()

    triggered: list[dict] = []
    now = datetime.now(UTC)

    for rule in rules:
        if rule.condition_entity_type == "ESGAction":
            triggered.extend(
                await _evaluate_action_rule(rule, organization_id, now, session)
            )

    for esc in triggered:
        os_counters.record_escalation()

    return triggered


async def _evaluate_action_rule(
    rule, organization_id: str, now: datetime, session: AsyncSession
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGActionModel
    stmt = select(ESGActionModel).where(
        ESGActionModel.organization_id == organization_id,
        ESGActionModel.action_status == rule.condition_status,
    )
    if rule.condition_priority:
        stmt = stmt.where(ESGActionModel.priority == rule.condition_priority)
    if rule.condition_overdue_days is not None:
        cutoff = now - timedelta(days=rule.condition_overdue_days)
        stmt = stmt.where(
            ESGActionModel.due_date < cutoff,
            ESGActionModel.action_status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"]),
        )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "rule_id": rule.id,
            "rule_name": rule.rule_name,
            "entity_type": "ESGAction",
            "entity_id": r.id,
            "escalate_to_role": rule.escalate_to_role,
            "escalate_to_user_id": rule.escalate_to_user_id,
            "message": rule.notification_message or f"Action '{r.title}' requires escalation",
            "triggered_at": now.isoformat(),
        }
        for r in rows
    ]


def _rule_to_dict(r) -> dict:
    return {
        "id": r.id,
        "organization_id": r.organization_id,
        "rule_name": r.rule_name,
        "condition_entity_type": r.condition_entity_type,
        "condition_status": r.condition_status,
        "condition_overdue_days": r.condition_overdue_days,
        "condition_priority": r.condition_priority,
        "escalate_to_role": r.escalate_to_role,
        "escalate_to_user_id": r.escalate_to_user_id,
        "notification_message": r.notification_message,
        "rule_status": r.rule_status,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
