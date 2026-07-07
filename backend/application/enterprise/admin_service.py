"""Delegated administration — assign enterprise, BU, and regional admin roles."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.user import UserModel

ENTERPRISE_SCOPE_ROLES = ("enterprise_admin", "bu_admin", "regional_admin")


async def assign_enterprise_role(
    enterprise_id: str,
    user_id: str,
    enterprise_scope: str,
    business_unit_id: str | None,
    region_id: str | None,
    actor_id: str,
    session: AsyncSession,
) -> UserModel | None:
    """
    Grant an enterprise-scoped administrative role to a user.

    enterprise_admin   — cross-enterprise visibility and administration
    bu_admin           — restricted to a specific BusinessUnit
    regional_admin     — restricted to a specific Region

    Access decisions are auditable: every assignment creates an AuditEvent.
    """
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None

    user.enterprise_id = enterprise_id
    user.enterprise_scope = enterprise_scope
    user.business_unit_id = business_unit_id if enterprise_scope == "bu_admin" else None
    user.region_id = region_id if enterprise_scope == "regional_admin" else None
    user.updated_at = datetime.now(UTC)

    now = datetime.now(UTC)
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action="enterprise.role_assigned",
            entity_type="User",
            entity_id=user_id,
            actor_id=actor_id,
            outcome="success",
            detail=f"User {user_id} assigned enterprise scope '{enterprise_scope}'",
            event_metadata={
                "enterprise_id": enterprise_id,
                "enterprise_scope": enterprise_scope,
                "business_unit_id": business_unit_id,
                "region_id": region_id,
            },
        )
    )
    return user


async def revoke_enterprise_role(
    user_id: str,
    actor_id: str,
    session: AsyncSession,
) -> bool:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    user.enterprise_id = None
    user.enterprise_scope = None
    user.business_unit_id = None
    user.region_id = None
    user.updated_at = datetime.now(UTC)

    now = datetime.now(UTC)
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action="enterprise.role_revoked",
            entity_type="User",
            entity_id=user_id,
            actor_id=actor_id,
            outcome="success",
            detail=f"Enterprise role revoked from user {user_id}",
            event_metadata={},
        )
    )
    return True


async def list_enterprise_admins(enterprise_id: str, session: AsyncSession) -> list[UserModel]:
    result = await session.execute(
        select(UserModel).where(
            UserModel.enterprise_id == enterprise_id,
            UserModel.enterprise_scope.isnot(None),
        )
    )
    return list(result.scalars().all())
