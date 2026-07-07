"""Enterprise policy and retention rule management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.enterprise import (
    EnterprisePolicyModel,
    NotificationPolicyModel,
    RetentionRuleModel,
)


async def _log(
    session: AsyncSession,
    action: str,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    detail: str = "",
) -> None:
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
    )


# ── Enterprise Policy ─────────────────────────────────────────────────────────


async def create_policy(
    enterprise_id: str,
    policy_type: str,
    name: str,
    description: str | None,
    config: dict,
    cascade_to_children: bool,
    scope: str,
    scope_id: str | None,
    actor_id: str,
    session: AsyncSession,
) -> EnterprisePolicyModel:
    now = datetime.now(UTC)
    policy = EnterprisePolicyModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        policy_type=policy_type,
        name=name,
        description=description,
        config=config,
        cascade_to_children=cascade_to_children,
        scope=scope,
        scope_id=scope_id,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(policy)
    await session.flush()
    await _log(
        session,
        "policy.created",
        actor_id,
        "EnterprisePolicy",
        policy.id,
        f"Policy '{name}' ({policy_type}) created",
    )
    return policy


async def list_policies(enterprise_id: str, session: AsyncSession) -> list[EnterprisePolicyModel]:
    result = await session.execute(
        select(EnterprisePolicyModel).where(
            EnterprisePolicyModel.enterprise_id == enterprise_id,
            EnterprisePolicyModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_policy(policy_id: str, session: AsyncSession) -> EnterprisePolicyModel | None:
    result = await session.execute(
        select(EnterprisePolicyModel).where(EnterprisePolicyModel.id == policy_id)
    )
    return result.scalar_one_or_none()


async def deactivate_policy(policy_id: str, actor_id: str, session: AsyncSession) -> bool:
    policy = await get_policy(policy_id, session)
    if not policy:
        return False
    policy.is_active = False
    policy.updated_at = datetime.now(UTC)
    await _log(session, "policy.deactivated", actor_id, "EnterprisePolicy", policy_id)
    return True


# ── Retention Rule ────────────────────────────────────────────────────────────


async def create_retention_rule(
    enterprise_id: str,
    entity_type: str,
    retention_days: int,
    cascade_to_children: bool,
    legal_hold: bool,
    description: str | None,
    actor_id: str,
    session: AsyncSession,
) -> RetentionRuleModel:
    now = datetime.now(UTC)
    rule = RetentionRuleModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        entity_type=entity_type,
        retention_days=retention_days,
        cascade_to_children=cascade_to_children,
        legal_hold=legal_hold,
        description=description,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    await session.flush()
    await _log(
        session,
        "retention.rule_created",
        actor_id,
        "RetentionRule",
        rule.id,
        f"Retention rule for {entity_type}: {retention_days} days",
    )
    return rule


async def list_retention_rules(
    enterprise_id: str, session: AsyncSession
) -> list[RetentionRuleModel]:
    result = await session.execute(
        select(RetentionRuleModel).where(
            RetentionRuleModel.enterprise_id == enterprise_id,
            RetentionRuleModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


# ── Notification Policy ───────────────────────────────────────────────────────


async def create_notification_policy(
    enterprise_id: str,
    name: str,
    escalation_routes: list,
    regional_routes: dict,
    executive_routes: list,
    actor_id: str,
    session: AsyncSession,
) -> NotificationPolicyModel:
    now = datetime.now(UTC)
    np = NotificationPolicyModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        name=name,
        escalation_routes=escalation_routes,
        regional_routes=regional_routes,
        executive_routes=executive_routes,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(np)
    await session.flush()
    await _log(
        session,
        "notification_policy.created",
        actor_id,
        "NotificationPolicy",
        np.id,
        f"Notification policy '{name}' created",
    )
    return np


async def list_notification_policies(
    enterprise_id: str, session: AsyncSession
) -> list[NotificationPolicyModel]:
    result = await session.execute(
        select(NotificationPolicyModel).where(
            NotificationPolicyModel.enterprise_id == enterprise_id,
            NotificationPolicyModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
