"""M39 ESG Objective and Key Result services.

Key result progress rollup:
  progress_percent = (current_value / target_value) * 100   if target_value > 0
  objective_status is derived deterministically from average key result progress.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from application.operating_system.metrics import os_counters


async def _log_audit(session: AsyncSession, action: str, entity_id: str,
                     organization_id: str, detail: str = "") -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel
    evt = AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type="ESGObjective",
        entity_id=entity_id,
        actor_id=None,
        outcome="success",
        detail=detail,
        event_metadata={"organization_id": organization_id},
    )
    session.add(evt)


# ── Objectives ────────────────────────────────────────────────────────────────

async def create_objective(
    organization_id: str,
    title: str,
    description: str,
    category: str,
    session: AsyncSession,
    owner_user_id: str | None = None,
    target_value: float | None = None,
    unit: str | None = None,
    due_date: datetime | None = None,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGObjectiveModel
    now = datetime.now(UTC)
    obj = ESGObjectiveModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        title=title,
        description=description,
        category=category,
        owner_user_id=owner_user_id,
        target_value=target_value,
        current_value=0.0,
        unit=unit,
        due_date=due_date,
        objective_status="NOT_STARTED",
    )
    session.add(obj)
    await session.flush()
    os_counters.record_objective_created()
    await _log_audit(session, "objective.created", obj.id, organization_id,
                     detail=f"title={title} category={category}")
    return _obj_to_dict(obj)


async def list_objectives(
    organization_id: str,
    session: AsyncSession,
    category: str | None = None,
    objective_status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGObjectiveModel
    stmt = select(ESGObjectiveModel).where(
        ESGObjectiveModel.organization_id == organization_id
    )
    if category:
        stmt = stmt.where(ESGObjectiveModel.category == category)
    if objective_status:
        stmt = stmt.where(ESGObjectiveModel.objective_status == objective_status)
    stmt = stmt.order_by(ESGObjectiveModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_obj_to_dict(r) for r in rows]


async def get_objective(
    organization_id: str, objective_id: str, session: AsyncSession
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGObjectiveModel
    stmt = select(ESGObjectiveModel).where(
        ESGObjectiveModel.organization_id == organization_id,
        ESGObjectiveModel.id == objective_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _obj_to_dict(row) if row else None


async def update_objective(
    organization_id: str,
    objective_id: str,
    session: AsyncSession,
    **fields,
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGObjectiveModel
    stmt = select(ESGObjectiveModel).where(
        ESGObjectiveModel.organization_id == organization_id,
        ESGObjectiveModel.id == objective_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    action = "objective.completed" if fields.get("objective_status") == "COMPLETED" \
        else "objective.updated"
    await _log_audit(session, action, row.id, organization_id)
    return _obj_to_dict(row)


# ── Key Results ───────────────────────────────────────────────────────────────

async def create_key_result(
    organization_id: str,
    objective_id: str,
    title: str,
    metric_name: str,
    target_value: float,
    session: AsyncSession,
    current_value: float = 0.0,
) -> dict:
    from infrastructure.persistence.models.operating_system import ESGKeyResultModel
    progress = _calc_progress(current_value, target_value)
    now = datetime.now(UTC)
    kr = ESGKeyResultModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        objective_id=objective_id,
        title=title,
        metric_name=metric_name,
        target_value=target_value,
        current_value=current_value,
        progress_percent=progress,
        kr_status=_status_from_progress(progress),
    )
    session.add(kr)
    await session.flush()
    await _rollup_objective_status(organization_id, objective_id, session)
    return _kr_to_dict(kr)


async def update_key_result(
    organization_id: str,
    kr_id: str,
    session: AsyncSession,
    current_value: float | None = None,
    **fields,
) -> dict | None:
    from infrastructure.persistence.models.operating_system import ESGKeyResultModel
    stmt = select(ESGKeyResultModel).where(
        ESGKeyResultModel.organization_id == organization_id,
        ESGKeyResultModel.id == kr_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if current_value is not None:
        row.current_value = current_value
        row.progress_percent = _calc_progress(current_value, row.target_value)
        row.kr_status = _status_from_progress(row.progress_percent)
    for k, v in fields.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    await _rollup_objective_status(organization_id, row.objective_id, session)
    return _kr_to_dict(row)


async def list_key_results(
    organization_id: str, objective_id: str, session: AsyncSession
) -> list[dict]:
    from infrastructure.persistence.models.operating_system import ESGKeyResultModel
    stmt = select(ESGKeyResultModel).where(
        ESGKeyResultModel.organization_id == organization_id,
        ESGKeyResultModel.objective_id == objective_id,
    ).order_by(ESGKeyResultModel.created_at.asc())
    rows = (await session.execute(stmt)).scalars().all()
    return [_kr_to_dict(r) for r in rows]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _calc_progress(current: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return min(100.0, round((current / target) * 100, 2))


def _status_from_progress(progress: float) -> str:
    if progress >= 100:
        return "COMPLETED"
    if progress >= 70:
        return "ON_TRACK"
    if progress >= 40:
        return "AT_RISK"
    return "OFF_TRACK"


async def _rollup_objective_status(
    organization_id: str, objective_id: str, session: AsyncSession
) -> None:
    """Recompute objective status from the mean progress of its key results."""
    from infrastructure.persistence.models.operating_system import (
        ESGKeyResultModel, ESGObjectiveModel,
    )
    avg_stmt = select(func.avg(ESGKeyResultModel.progress_percent)).where(
        ESGKeyResultModel.organization_id == organization_id,
        ESGKeyResultModel.objective_id == objective_id,
    )
    avg = (await session.execute(avg_stmt)).scalar_one_or_none() or 0.0

    obj_stmt = select(ESGObjectiveModel).where(
        ESGObjectiveModel.organization_id == organization_id,
        ESGObjectiveModel.id == objective_id,
    )
    obj = (await session.execute(obj_stmt)).scalar_one_or_none()
    if obj and obj.objective_status != "COMPLETED":
        obj.objective_status = _status_from_progress(float(avg))
        obj.current_value = float(avg)
        obj.updated_at = datetime.now(UTC)


def _obj_to_dict(o) -> dict:
    return {
        "id": o.id,
        "organization_id": o.organization_id,
        "title": o.title,
        "description": o.description,
        "category": o.category,
        "owner_user_id": o.owner_user_id,
        "target_value": o.target_value,
        "current_value": o.current_value,
        "unit": o.unit,
        "due_date": o.due_date,
        "objective_status": o.objective_status,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


def _kr_to_dict(k) -> dict:
    return {
        "id": k.id,
        "organization_id": k.organization_id,
        "objective_id": k.objective_id,
        "title": k.title,
        "metric_name": k.metric_name,
        "target_value": k.target_value,
        "current_value": k.current_value,
        "progress_percent": k.progress_percent,
        "kr_status": k.kr_status,
        "created_at": k.created_at,
        "updated_at": k.updated_at,
    }
