"""M35 Remediation Plan Service.

Manages supplier-owned remediation plans for findings.

Internal:
  create_remediation_plan()  — internal user creates plan for a supplier
  verify_plan()              — mark a completed plan as verified
  list_plans_for_org()       — list all plans visible to an organisation

Supplier:
  get_my_plans()             — supplier sees only their own plans
  update_progress()          — supplier updates completion_percentage / status
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def _log_activity(
    supplier_id: str,
    supplier_user_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    session,
    metadata: dict | None = None,
) -> None:
    import json

    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    now = datetime.now(UTC)
    model = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("remediation_activity_log_failed", error=str(exc))


async def create_remediation_plan(
    supplier_id: str,
    finding_id: str,
    title: str,
    description: str,
    organization_id: str,
    created_by: str,
    due_date: datetime | None = None,
    owner_supplier_user_id: str | None = None,
    session=None,
) -> object:
    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    now = datetime.now(UTC)
    model = RemediationPlanModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        finding_id=finding_id,
        organization_id=organization_id,
        title=title,
        description=description,
        owner_supplier_user_id=owner_supplier_user_id,
        due_date=due_date,
        remediation_status="open",
        completion_percentage=0,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()
    logger.info(
        "remediation_plan_created",
        plan_id=model.id,
        supplier_id=supplier_id,
        finding_id=finding_id,
    )
    return model


async def get_my_plans(
    supplier_id: str,
    status: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    stmt = select(RemediationPlanModel).where(RemediationPlanModel.supplier_id == supplier_id)
    if status:
        stmt = stmt.where(RemediationPlanModel.remediation_status == status)
    stmt = stmt.order_by(RemediationPlanModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_plan(
    plan_id: str,
    supplier_id: str,
    session=None,
) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    stmt = select(RemediationPlanModel).where(
        RemediationPlanModel.id == plan_id,
        RemediationPlanModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_progress(
    plan_id: str,
    supplier_id: str,
    completion_percentage: int,
    new_status: str | None = None,
    session=None,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    if not (0 <= completion_percentage <= 100):
        raise ValueError("completion_percentage must be between 0 and 100")

    stmt = select(RemediationPlanModel).where(
        RemediationPlanModel.id == plan_id,
        RemediationPlanModel.supplier_id == supplier_id,
    )
    plan = (await session.execute(stmt)).scalar_one_or_none()
    if plan is None:
        raise ValueError("Remediation plan not found")
    if plan.remediation_status == "verified":
        raise ValueError("Cannot update a verified remediation plan")

    # F4: prevent rollback from completed status
    if plan.remediation_status == "completed" and new_status in ("open", "in_progress"):
        raise ValueError("Cannot roll back a completed remediation plan to an earlier status")

    now = datetime.now(UTC)
    plan.completion_percentage = completion_percentage
    plan.updated_at = now

    if new_status:
        _ALLOWED = {"open", "in_progress", "completed"}
        if new_status not in _ALLOWED:
            raise ValueError(f"Invalid status. Allowed: {_ALLOWED}")
        plan.remediation_status = new_status
    elif completion_percentage == 100 and plan.remediation_status != "completed":
        plan.remediation_status = "completed"
    elif completion_percentage > 0 and plan.remediation_status == "open":
        plan.remediation_status = "in_progress"

    await session.flush()

    # F5: activity audit
    await _log_activity(
        supplier_id=supplier_id,
        supplier_user_id=plan.owner_supplier_user_id,
        event_type="remediation_progress_updated",
        entity_type="remediation_plan",
        entity_id=plan_id,
        metadata={
            "completion_percentage": completion_percentage,
            "status": plan.remediation_status,
        },
        session=session,
    )
    return plan


async def verify_plan(
    plan_id: str,
    organization_id: str,
    verified_by: str,
    session=None,
) -> object:
    """Internal user verifies a completed remediation plan."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    # F3: SELECT FOR UPDATE to serialize concurrent verifiers
    stmt = (
        select(RemediationPlanModel)
        .where(
            RemediationPlanModel.id == plan_id,
            RemediationPlanModel.organization_id == organization_id,
            RemediationPlanModel.remediation_status == "completed",
        )
        .with_for_update()
    )
    plan = (await session.execute(stmt)).scalar_one_or_none()
    if plan is None:
        raise ValueError("Plan not found, not completed, or not in your organisation")

    now = datetime.now(UTC)
    plan.remediation_status = "verified"
    plan.verified_by = verified_by
    plan.verified_at = now
    plan.updated_at = now
    await session.flush()

    # F5: activity audit
    await _log_activity(
        supplier_id=plan.supplier_id,
        supplier_user_id=None,
        event_type="remediation_verified",
        entity_type="remediation_plan",
        entity_id=plan_id,
        metadata={"verified_by": verified_by},
        session=session,
    )
    return plan


async def list_plans_for_org(
    organization_id: str,
    supplier_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import RemediationPlanModel

    stmt = select(RemediationPlanModel).where(
        RemediationPlanModel.organization_id == organization_id
    )
    if supplier_id:
        stmt = stmt.where(RemediationPlanModel.supplier_id == supplier_id)
    if status:
        stmt = stmt.where(RemediationPlanModel.remediation_status == status)
    stmt = stmt.order_by(RemediationPlanModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
