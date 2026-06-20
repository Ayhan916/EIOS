"""M39 Accountability Assignment Service.

Tracks OWNER | REVIEWER | APPROVER | EXECUTIVE_SPONSOR roles
for any EIOS entity without hard FK dependencies.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

VALID_ROLES = {"OWNER", "REVIEWER", "APPROVER", "EXECUTIVE_SPONSOR"}


async def _log_audit(session, action: str, entity_id: str, organization_id: str, detail: str = "") -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel
    session.add(AuditEventModel(
        id=str(uuid.uuid4()), status="Active", version=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        action=action, entity_type="AccountabilityAssignment", entity_id=entity_id,
        actor_id=None, outcome="success", detail=detail,
        event_metadata={"organization_id": organization_id},
    ))


async def assign_accountability(
    organization_id: str,
    entity_type: str,
    entity_id: str,
    role: str,
    assigned_to_user_id: str,
    session: AsyncSession,
    assigned_by_user_id: str | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import AccountabilityAssignmentModel
    now = datetime.now(UTC)
    assignment = AccountabilityAssignmentModel(
        id=str(uuid.uuid4()), status="Active", version=1, created_at=now, updated_at=now,
        organization_id=organization_id, entity_type=entity_type, entity_id=entity_id,
        role=role, assigned_to_user_id=assigned_to_user_id,
        assigned_by_user_id=assigned_by_user_id, assigned_at=now,
        assignment_status="ACTIVE",
    )
    session.add(assignment)
    await session.flush()
    await _log_audit(session, "accountability.assigned", assignment.id, organization_id,
                     detail=f"entity={entity_type}:{entity_id} role={role} user={assigned_to_user_id}")
    from application.operating_system.metrics import os_counters
    os_counters.record_accountability_assignment_created()
    return _to_dict(assignment)


async def list_assignments(
    organization_id: str, session: AsyncSession,
    entity_type: str | None = None, entity_id: str | None = None,
    role: str | None = None, limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import AccountabilityAssignmentModel
    stmt = select(AccountabilityAssignmentModel).where(
        AccountabilityAssignmentModel.organization_id == organization_id,
        AccountabilityAssignmentModel.assignment_status == "ACTIVE",
    )
    if entity_type:
        stmt = stmt.where(AccountabilityAssignmentModel.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AccountabilityAssignmentModel.entity_id == entity_id)
    if role:
        stmt = stmt.where(AccountabilityAssignmentModel.role == role)
    stmt = stmt.order_by(AccountabilityAssignmentModel.assigned_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_assignment(
    organization_id: str, assignment_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import AccountabilityAssignmentModel
    stmt = select(AccountabilityAssignmentModel).where(
        AccountabilityAssignmentModel.organization_id == organization_id,
        AccountabilityAssignmentModel.id == assignment_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def remove_assignment(
    organization_id: str, assignment_id: str, session: AsyncSession
) -> bool:
    from infrastructure.persistence.models.operating_system import AccountabilityAssignmentModel
    stmt = select(AccountabilityAssignmentModel).where(
        AccountabilityAssignmentModel.organization_id == organization_id,
        AccountabilityAssignmentModel.id == assignment_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return False
    row.assignment_status = "REMOVED"
    row.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(session, "accountability.removed", row.id, organization_id,
                     detail=f"entity={row.entity_type}:{row.entity_id} role={row.role}")
    return True


def _to_dict(a) -> dict:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "role": a.role,
        "assigned_to_user_id": a.assigned_to_user_id,
        "assigned_by_user_id": a.assigned_by_user_id,
        "assigned_at": a.assigned_at,
        "assignment_status": a.assignment_status,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }
