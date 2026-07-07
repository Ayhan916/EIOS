"""M39 Control Test Service — point-in-time effectiveness tests for ESGControls.

test_result lifecycle: PASS → EFFECTIVE, PARTIAL → PARTIALLY_EFFECTIVE, FAIL → INEFFECTIVE.
Updates parent ESGControl.effectiveness_status on each create.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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
            entity_type="ControlTest",
            entity_id=entity_id,
            actor_id=None,
            outcome="success",
            detail=detail,
            event_metadata={"organization_id": organization_id},
        )
    )


def _result_to_effectiveness(test_result: str) -> str:
    if test_result == "PASS":
        return "EFFECTIVE"
    if test_result == "PARTIAL":
        return "PARTIALLY_EFFECTIVE"
    return "INEFFECTIVE"


async def create_test(
    organization_id: str,
    control_id: str,
    test_result: str,
    tested_at: datetime,
    session: AsyncSession,
    performed_by: str | None = None,
    findings: str = "",
) -> dict:
    from infrastructure.persistence.models.operating_system import ControlTestModel, ESGControlModel

    now = datetime.now(UTC)
    test = ControlTestModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        control_id=control_id,
        performed_by=performed_by,
        test_result=test_result,
        findings=findings,
        tested_at=tested_at,
    )
    session.add(test)
    await session.flush()

    ctrl_stmt = select(ESGControlModel).where(
        ESGControlModel.organization_id == organization_id,
        ESGControlModel.id == control_id,
    )
    ctrl = (await session.execute(ctrl_stmt)).scalar_one_or_none()
    if ctrl:
        ctrl.effectiveness_status = _result_to_effectiveness(test_result)
        ctrl.updated_at = now

    await _log_audit(
        session,
        "control.tested",
        test.id,
        organization_id,
        detail=f"control={control_id} result={test_result}",
    )
    from application.operating_system.metrics import os_counters

    os_counters.record_control_test_created()
    return _to_dict(test)


async def list_tests(
    organization_id: str,
    session: AsyncSession,
    control_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ControlTestModel

    stmt = select(ControlTestModel).where(ControlTestModel.organization_id == organization_id)
    if control_id:
        stmt = stmt.where(ControlTestModel.control_id == control_id)
    stmt = stmt.order_by(ControlTestModel.tested_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_dict(r) for r in rows]


async def update_test(
    organization_id: str, test_id: str, session: AsyncSession, **fields
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ControlTestModel

    stmt = select(ControlTestModel).where(
        ControlTestModel.organization_id == organization_id,
        ControlTestModel.id == test_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    await _log_audit(session, "control.tested", row.id, organization_id)
    return _to_dict(row)


async def delete_test(organization_id: str, test_id: str, session: AsyncSession) -> bool:
    from infrastructure.persistence.models.operating_system import ControlTestModel

    stmt = select(ControlTestModel).where(
        ControlTestModel.organization_id == organization_id,
        ControlTestModel.id == test_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


def _to_dict(t) -> dict:
    return {
        "id": t.id,
        "organization_id": t.organization_id,
        "control_id": t.control_id,
        "performed_by": t.performed_by,
        "test_result": t.test_result,
        "findings": t.findings,
        "tested_at": t.tested_at,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
