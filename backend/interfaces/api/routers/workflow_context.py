"""Workflow context router — pipeline chain for the Lieferketten-Sorgfalt workflow."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from application.workflow.context_service import (
    WorkflowContext,
    WorkflowStepInfo,
    get_workflow_context,
)
from domain.user import User
from interfaces.api.deps import get_current_user, get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/workflow",
    tags=["workflow"],
    dependencies=[Depends(get_current_user)],
)

_ALLOWED_TYPES = {"assessment", "finding", "risk", "recommendation", "cap"}


class WorkflowStepResponse(BaseModel):
    key: str
    label: str
    count: int
    status: str
    current: bool
    route: str | None
    entities: list[dict]
    next_action_label: str | None
    next_action_route: str | None

    model_config = {"from_attributes": True}


class WorkflowContextResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    entity_type: str
    entity_id: str
    assessment_id: str | None
    supplier_id: str | None
    supplier_name: str | None
    steps: list[WorkflowStepResponse]
    completion_pct: int
    next_step: WorkflowStepResponse | None

    model_config = {"from_attributes": True}


def _step_to_response(s: WorkflowStepInfo) -> WorkflowStepResponse:
    return WorkflowStepResponse(
        key=s.key,
        label=s.label,
        count=s.count,
        status=s.status,
        current=s.current,
        route=s.route,
        entities=s.entities,
        next_action_label=s.next_action_label,
        next_action_route=s.next_action_route,
    )


@router.get("/context/{entity_type}/{entity_id}", response_model=WorkflowContextResponse)
async def get_context(
    entity_type: str,
    entity_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowContextResponse:
    if entity_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity_type must be one of: {', '.join(sorted(_ALLOWED_TYPES))}",
        )
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization")

    ctx = await get_workflow_context(entity_type, entity_id, user.organization_id, session)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found or access denied")

    return WorkflowContextResponse(
        workflow_id=ctx.workflow_id,
        workflow_name=ctx.workflow_name,
        entity_type=ctx.entity_type,
        entity_id=ctx.entity_id,
        assessment_id=ctx.assessment_id,
        supplier_id=ctx.supplier_id,
        supplier_name=ctx.supplier_name,
        steps=[_step_to_response(s) for s in ctx.steps],
        completion_pct=ctx.completion_pct,
        next_step=_step_to_response(ctx.next_step) if ctx.next_step else None,
    )
