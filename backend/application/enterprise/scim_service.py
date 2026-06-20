"""SCIM 2.0 provisioning endpoints — create, update, deactivate users.

This implements the SCIM 2.0 resource server interface for user provisioning.
The SCIM client (IdP) calls these endpoints to sync user lifecycles.
All provisioning actions are audited.

Note: Full SCIM 2.0 protocol (schemas endpoint, bulk, etags) is outside
this scope — this implements the core User resource operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.user import UserModel


async def _log_scim(
    session: AsyncSession,
    action: str,
    actor_id: str | None,
    entity_id: str,
    detail: str = "",
    metadata: dict | None = None,
) -> None:
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type="User",
        entity_id=entity_id,
        actor_id=actor_id,
        outcome="success",
        detail=detail,
        event_metadata=metadata or {},
    ))


async def scim_create_user(
    enterprise_id: str,
    organization_id: str,
    username: str,
    email: str,
    display_name: str,
    active: bool,
    groups: list[str],
    actor_id: str | None,
    session: AsyncSession,
) -> UserModel:
    """Create a user via SCIM provisioning."""
    now = datetime.now(UTC)
    user = UserModel(
        id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        role="viewer",  # default role; group mapping may override
        organization_id=organization_id,
        enterprise_id=enterprise_id,
        is_active=active,
        password_hash=None,  # SCIM users authenticate via SSO — no password
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    await _log_scim(
        session,
        "scim.user_created",
        actor_id,
        user.id,
        f"SCIM: user '{email}' provisioned",
        {"enterprise_id": enterprise_id, "groups": groups},
    )
    return user


async def scim_update_user(
    user_id: str,
    display_name: str | None,
    active: bool | None,
    actor_id: str | None,
    session: AsyncSession,
) -> UserModel | None:
    """Update a user via SCIM provisioning."""
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if display_name is not None:
        user.display_name = display_name
    if active is not None:
        user.is_active = active
    user.updated_at = datetime.now(UTC)
    await _log_scim(
        session,
        "scim.user_updated",
        actor_id,
        user_id,
        "SCIM: user updated",
        {"active": active},
    )
    return user


async def scim_deactivate_user(
    user_id: str, actor_id: str | None, session: AsyncSession
) -> bool:
    """Deactivate (soft-delete) a user via SCIM provisioning."""
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.is_active = False
    user.updated_at = datetime.now(UTC)
    await _log_scim(
        session,
        "scim.user_deactivated",
        actor_id,
        user_id,
        "SCIM: user deactivated",
    )
    return True
