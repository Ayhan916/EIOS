from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from domain.audit_event import AuditEvent
from infrastructure.persistence.repositories.audit_event import SQLAuditEventRepository
from interfaces.api.deps import get_audit_event_repo, get_current_user
from interfaces.api.schemas.audit import AuditEventResponse

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_user)],
)


def _to_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        action=event.action,
        actor_id=event.actor_id,
        actor_email=event.actor_email,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        outcome=event.outcome,
        detail=event.detail,
        event_metadata=event.event_metadata,
        created_at=event.created_at,
    )


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    action: str | None = Query(
        default=None, description="Filter by action (e.g. 'workflow.completed')"
    ),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> list[AuditEventResponse]:
    """List audit events with optional filters.

    All workflow completions, assessment creations, and authentication events
    are recorded here for regulatory compliance traceability.
    """
    if entity_type and entity_id:
        events = await repo.list_by_entity(entity_type, entity_id)
    elif actor_id:
        events = await repo.list_by_actor(actor_id)
    elif action:
        events = await repo.list_by_action(action)
    else:
        events = await repo.list_all()

    return [_to_response(e) for e in events]


@router.get("/events/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: str,
    repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> AuditEventResponse:
    event = await repo.get_by_id(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AuditEvent {event_id} not found"
        )
    return _to_response(event)


@router.get("/trail/{entity_type}/{entity_id}", response_model=list[AuditEventResponse])
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> list[AuditEventResponse]:
    """Full audit trail for a specific entity (WorkflowRun, Assessment, AgentRun, etc.)."""
    events = await repo.list_by_entity(entity_type, entity_id)
    return [_to_response(e) for e in events]
