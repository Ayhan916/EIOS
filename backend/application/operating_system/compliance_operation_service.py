"""M39 Compliance Operation Service.

Manages continuous compliance readiness operations per regulatory framework.
Integrates with M31 gap data via sync_from_m31() — idempotent upsert.

Framework name resolution priority:
  1. gap.framework          (application/compliance/gaps.py ComplianceGap)
  2. gap.regulation_name
  3. gap.framework_name
  4. regulation_code lookup from requirement_id prefix
  5. "UNKNOWN" fallback
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def resolve_framework_name(
    gap: object,
    requirement_to_regulation_code: dict[str, str] | None = None,
) -> str:
    """Return a deterministic framework name for a ComplianceGap.

    Tries multiple attribute paths so it works with both the
    application/compliance/gaps.py dataclass (has .framework) and the
    domain/compliance_gap.py dataclass (has .regulation_requirement_id).
    """
    for attr in ("framework", "regulation_name", "framework_name"):
        val = getattr(gap, attr, None)
        if val and str(val).strip():
            return str(val).strip()

    # Try lookup via requirement_id → regulation.code
    req_id = getattr(gap, "regulation_requirement_id", None)
    if req_id and requirement_to_regulation_code:
        code = requirement_to_regulation_code.get(req_id)
        if code:
            return code

    # Parse prefix from requirement_id ("CSRD-Art-5" → "CSRD")
    if req_id:
        prefix = str(req_id).split("-")[0].strip()
        if prefix and prefix != req_id:
            return prefix

    return "UNKNOWN"


async def _log_audit(
    session, action: str, entity_id: str, organization_id: str, detail: str = ""
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            action=action,
            entity_type="ComplianceOperation",
            entity_id=entity_id,
            actor_id=None,
            outcome="success",
            detail=detail,
            event_metadata={"organization_id": organization_id},
        )
    )


async def create_compliance_operation(
    organization_id: str,
    framework_name: str,
    session: AsyncSession,
    owner_user_id: str | None = None,
    coverage_percent: float = 0.0,
    gap_count: int = 0,
) -> dict:
    from infrastructure.persistence.models.operating_system import ComplianceOperationModel

    now = datetime.now(UTC)
    op = ComplianceOperationModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        framework_name=framework_name,
        coverage_percent=coverage_percent,
        gap_count=gap_count,
        owner_user_id=owner_user_id,
        operation_status="IN_PROGRESS",
        actions=[],
    )
    session.add(op)
    await session.flush()
    await _log_audit(
        session,
        "compliance_op.created",
        op.id,
        organization_id,
        detail=f"framework={framework_name}",
    )
    from application.operating_system.metrics import os_counters

    os_counters.record_compliance_op_created()
    return _to_dict(op)


async def list_compliance_operations(
    organization_id: str,
    session: AsyncSession,
    framework_name: str | None = None,
    operation_status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ComplianceOperationModel

    stmt = select(ComplianceOperationModel).where(
        ComplianceOperationModel.organization_id == organization_id
    )
    if framework_name:
        stmt = stmt.where(ComplianceOperationModel.framework_name == framework_name)
    if operation_status:
        stmt = stmt.where(ComplianceOperationModel.operation_status == operation_status)
    stmt = stmt.order_by(ComplianceOperationModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def get_compliance_operation(
    organization_id: str, operation_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ComplianceOperationModel

    stmt = select(ComplianceOperationModel).where(
        ComplianceOperationModel.organization_id == organization_id,
        ComplianceOperationModel.id == operation_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def update_compliance_operation(
    organization_id: str, operation_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ComplianceOperationModel

    stmt = select(ComplianceOperationModel).where(
        ComplianceOperationModel.organization_id == organization_id,
        ComplianceOperationModel.id == operation_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(session, "compliance_op.updated", row.id, organization_id)
    return _to_dict(row)


async def sync_from_m31(
    organization_id: str,
    framework_name: str,
    coverage_percent: float,
    gap_count: int,
    session: AsyncSession,
) -> dict:
    """Upsert a ComplianceOperation from M31 gap recalculation data.

    Idempotent: finds the existing operation for this org+framework and updates
    coverage/gap_count, or creates a new one.  Emits compliance_op.synced.
    """
    from infrastructure.persistence.models.operating_system import ComplianceOperationModel

    stmt = (
        select(ComplianceOperationModel)
        .where(
            ComplianceOperationModel.organization_id == organization_id,
            ComplianceOperationModel.framework_name == framework_name,
        )
        .limit(1)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing:
        existing.coverage_percent = coverage_percent
        existing.gap_count = gap_count
        existing.last_synced_at = now
        existing.updated_at = now
        await session.flush()
        await _log_audit(
            session,
            "compliance_op.synced",
            existing.id,
            organization_id,
            detail=f"framework={framework_name} coverage={coverage_percent} gaps={gap_count}",
        )
        return _to_dict(existing)
    op = ComplianceOperationModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        framework_name=framework_name,
        coverage_percent=coverage_percent,
        gap_count=gap_count,
        operation_status="IN_PROGRESS",
        actions=[],
        last_synced_at=now,
    )
    session.add(op)
    await session.flush()
    await _log_audit(
        session,
        "compliance_op.synced",
        op.id,
        organization_id,
        detail=f"framework={framework_name} coverage={coverage_percent} gaps={gap_count}",
    )
    return _to_dict(op)


def _to_dict(o) -> dict:
    return {
        "id": o.id,
        "organization_id": o.organization_id,
        "framework_name": o.framework_name,
        "coverage_percent": o.coverage_percent,
        "gap_count": o.gap_count,
        "owner_user_id": o.owner_user_id,
        "operation_status": o.operation_status,
        "actions": o.actions,
        "last_synced_at": o.last_synced_at,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }
