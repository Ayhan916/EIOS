"""M39 ESG Operating System API Router.

Prefix: /api/v1/operating-system

Scopes:
  operating_system:read  — read objectives, initiatives, actions, dashboard
  operating_system:write — create / update objectives, initiatives, actions, etc.

Tenant isolation: all reads and writes scoped to current_user.organization_id.
Cross-tenant access returns 404.

Governance constraint: agents may never approve workflow steps, close strategic risks,
or complete initiatives — human approval is enforced at the service layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.api.deps import get_current_user, get_db, require_analyst, require_admin
from interfaces.api.schemas.operating_system import (
    AccountabilityAssignmentResponse,
    ApproveWorkflowStepRequest,
    AssignAccountabilityRequest,
    CalendarEventResponse,
    ComplianceOperationResponse,
    ControlTestResponse,
    CreateActionRequest,
    CreateCalendarEventRequest,
    CreateComplianceOperationRequest,
    CreateControlRequest,
    CreateControlTestRequest,
    CreateEscalationRuleRequest,
    CreateInitiativeRequest,
    CreateKeyResultRequest,
    CreateObjectiveRequest,
    CreatePlaybookRequest,
    CreateProgramRequest,
    CreateStrategicRiskRequest,
    ESGActionResponse,
    ESGControlResponse,
    ESGHealthScoreResponse,
    ESGInitiativeResponse,
    ESGKeyResultResponse,
    ESGObjectiveResponse,
    ESGPlaybookResponse,
    ESGProgramResponse,
    EscalationRuleResponse,
    EscalationTriggeredResponse,
    OperatingSystemDashboard,
    RejectWorkflowStepRequest,
    StartWorkflowRequest,
    StrategicRiskResponse,
    TimelineEntry,
    UpdateActionRequest,
    UpdateCalendarEventRequest,
    UpdateComplianceOperationRequest,
    UpdateControlRequest,
    UpdateControlTestRequest,
    UpdateInitiativeRequest,
    UpdateObjectiveRequest,
    UpdateProgramRequest,
    UpdateStrategicRiskRequest,
    WorkflowExecutionResponse,
)

router = APIRouter(
    prefix="/operating-system",
    tags=["ESG Operating System (M39)"],
)

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)


# ── Objectives ────────────────────────────────────────────────────────────────

@router.get(
    "/objectives",
    response_model=list[ESGObjectiveResponse],
    dependencies=[_ANALYST],
)
async def list_objectives(
    category: str | None = None,
    objective_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGObjectiveResponse]:
    from application.operating_system.objective_service import list_objectives
    rows = await list_objectives(
        organization_id=current_user.organization_id,
        category=category,
        objective_status=objective_status,
        limit=limit,
        session=session,
    )
    return [ESGObjectiveResponse(**r) for r in rows]


@router.post(
    "/objectives",
    response_model=ESGObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_objective(
    body: CreateObjectiveRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGObjectiveResponse:
    from application.operating_system.objective_service import create_objective
    row = await create_objective(
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        category=body.category,
        owner_user_id=body.owner_user_id,
        target_value=body.target_value,
        unit=body.unit,
        due_date=body.due_date,
        session=session,
    )
    return ESGObjectiveResponse(**row)


@router.get(
    "/objectives/{objective_id}",
    response_model=ESGObjectiveResponse,
    dependencies=[_ANALYST],
)
async def get_objective(
    objective_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGObjectiveResponse:
    from application.operating_system.objective_service import get_objective
    row = await get_objective(current_user.organization_id, objective_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return ESGObjectiveResponse(**row)


@router.patch(
    "/objectives/{objective_id}",
    response_model=ESGObjectiveResponse,
    dependencies=[_ANALYST],
)
async def update_objective(
    objective_id: str,
    body: UpdateObjectiveRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGObjectiveResponse:
    from application.operating_system.objective_service import update_objective
    updates = body.model_dump(exclude_none=True)
    row = await update_objective(
        current_user.organization_id, objective_id, session, **updates
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return ESGObjectiveResponse(**row)


# ── Key Results ───────────────────────────────────────────────────────────────

@router.get(
    "/objectives/{objective_id}/key-results",
    response_model=list[ESGKeyResultResponse],
    dependencies=[_ANALYST],
)
async def list_key_results(
    objective_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGKeyResultResponse]:
    from application.operating_system.objective_service import list_key_results, get_objective
    if await get_objective(current_user.organization_id, objective_id, session) is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    rows = await list_key_results(current_user.organization_id, objective_id, session)
    return [ESGKeyResultResponse(**r) for r in rows]


@router.post(
    "/objectives/{objective_id}/key-results",
    response_model=ESGKeyResultResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_key_result(
    objective_id: str,
    body: CreateKeyResultRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGKeyResultResponse:
    from application.operating_system.objective_service import create_key_result, get_objective
    if await get_objective(current_user.organization_id, objective_id, session) is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    row = await create_key_result(
        organization_id=current_user.organization_id,
        objective_id=objective_id,
        title=body.title,
        metric_name=body.metric_name,
        target_value=body.target_value,
        current_value=body.current_value,
        session=session,
    )
    return ESGKeyResultResponse(**row)


# ── Initiatives ───────────────────────────────────────────────────────────────

@router.get(
    "/initiatives",
    response_model=list[ESGInitiativeResponse],
    dependencies=[_ANALYST],
)
async def list_initiatives(
    initiative_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGInitiativeResponse]:
    from application.operating_system.initiative_service import list_initiatives
    rows = await list_initiatives(
        current_user.organization_id, session,
        initiative_status=initiative_status, limit=limit,
    )
    return [ESGInitiativeResponse(**r) for r in rows]


@router.post(
    "/initiatives",
    response_model=ESGInitiativeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_initiative(
    body: CreateInitiativeRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGInitiativeResponse:
    from application.operating_system.initiative_service import create_initiative
    row = await create_initiative(
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        owner_user_id=body.owner_user_id,
        due_date=body.due_date,
        linked_objectives=body.linked_objectives,
        linked_suppliers=body.linked_suppliers,
        linked_findings=body.linked_findings,
        linked_risks=body.linked_risks,
        session=session,
    )
    return ESGInitiativeResponse(**row)


@router.get(
    "/initiatives/{initiative_id}",
    response_model=ESGInitiativeResponse,
    dependencies=[_ANALYST],
)
async def get_initiative(
    initiative_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGInitiativeResponse:
    from application.operating_system.initiative_service import get_initiative
    row = await get_initiative(current_user.organization_id, initiative_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return ESGInitiativeResponse(**row)


@router.patch(
    "/initiatives/{initiative_id}",
    response_model=ESGInitiativeResponse,
    dependencies=[_ANALYST],
)
async def update_initiative(
    initiative_id: str,
    body: UpdateInitiativeRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGInitiativeResponse:
    from application.operating_system.initiative_service import update_initiative
    row = await update_initiative(
        current_user.organization_id, initiative_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return ESGInitiativeResponse(**row)


# ── Actions ───────────────────────────────────────────────────────────────────

@router.get(
    "/actions",
    response_model=list[ESGActionResponse],
    dependencies=[_ANALYST],
)
async def list_actions(
    action_status: str | None = None,
    priority: str | None = None,
    source_type: str | None = None,
    overdue_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGActionResponse]:
    from application.operating_system.action_service import list_actions
    rows = await list_actions(
        current_user.organization_id, session,
        action_status=action_status, priority=priority,
        source_type=source_type, overdue_only=overdue_only, limit=limit,
    )
    return [ESGActionResponse(**r) for r in rows]


@router.post(
    "/actions",
    response_model=ESGActionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_action(
    body: CreateActionRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGActionResponse:
    from application.operating_system.action_service import create_action
    row = await create_action(
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        source_type=body.source_type,
        source_id=body.source_id,
        owner_user_id=body.owner_user_id,
        due_date=body.due_date,
        priority=body.priority,
        linked_objectives=body.linked_objectives,
        session=session,
    )
    return ESGActionResponse(**row)


@router.get(
    "/actions/{action_id}",
    response_model=ESGActionResponse,
    dependencies=[_ANALYST],
)
async def get_action(
    action_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGActionResponse:
    from application.operating_system.action_service import get_action
    row = await get_action(current_user.organization_id, action_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return ESGActionResponse(**row)


@router.patch(
    "/actions/{action_id}",
    response_model=ESGActionResponse,
    dependencies=[_ANALYST],
)
async def update_action(
    action_id: str,
    body: UpdateActionRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGActionResponse:
    from application.operating_system.action_service import update_action
    row = await update_action(
        current_user.organization_id, action_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return ESGActionResponse(**row)


# ── Playbooks ─────────────────────────────────────────────────────────────────

@router.get(
    "/playbooks",
    response_model=list[ESGPlaybookResponse],
    dependencies=[_ANALYST],
)
async def list_playbooks(
    playbook_type: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGPlaybookResponse]:
    from application.operating_system.playbook_service import list_playbooks
    rows = await list_playbooks(current_user.organization_id, session, playbook_type)
    return [ESGPlaybookResponse(**r) for r in rows]


@router.post(
    "/playbooks",
    response_model=ESGPlaybookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_playbook(
    body: CreatePlaybookRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGPlaybookResponse:
    from application.operating_system.playbook_service import create_playbook
    row = await create_playbook(
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        playbook_type=body.playbook_type,
        steps=body.steps,
        escalation_rules=body.escalation_rules,
        evidence_required=body.evidence_required,
        session=session,
    )
    return ESGPlaybookResponse(**row)


@router.get(
    "/playbooks/{playbook_id}",
    response_model=ESGPlaybookResponse,
    dependencies=[_ANALYST],
)
async def get_playbook(
    playbook_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGPlaybookResponse:
    from application.operating_system.playbook_service import get_playbook
    row = await get_playbook(current_user.organization_id, playbook_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return ESGPlaybookResponse(**row)


# ── Workflows ─────────────────────────────────────────────────────────────────

@router.get(
    "/workflows",
    response_model=list[WorkflowExecutionResponse],
    dependencies=[_ANALYST],
)
async def list_workflows(
    execution_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[WorkflowExecutionResponse]:
    from application.operating_system.playbook_service import list_workflow_executions
    rows = await list_workflow_executions(
        current_user.organization_id, session,
        execution_status=execution_status, limit=limit,
    )
    return [WorkflowExecutionResponse(**r) for r in rows]


@router.post(
    "/workflows",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def start_workflow(
    body: StartWorkflowRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowExecutionResponse:
    from application.operating_system.playbook_service import start_workflow
    row = await start_workflow(
        organization_id=current_user.organization_id,
        workflow_type=body.workflow_type,
        playbook_id=body.playbook_id,
        linked_entity_type=body.linked_entity_type,
        linked_entity_id=body.linked_entity_id,
        initiated_by=current_user.id,
        session=session,
    )
    return WorkflowExecutionResponse(**row)


@router.post(
    "/workflows/{execution_id}/approve",
    response_model=WorkflowExecutionResponse,
    dependencies=[_ANALYST],
)
async def approve_workflow_step(
    execution_id: str,
    body: ApproveWorkflowStepRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowExecutionResponse:
    from application.operating_system.playbook_service import approve_workflow_step
    row = await approve_workflow_step(
        organization_id=current_user.organization_id,
        execution_id=execution_id,
        approved_by=current_user.id,
        step_note=body.step_note,
        session=session,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    return WorkflowExecutionResponse(**row)


@router.post(
    "/workflows/{execution_id}/reject",
    response_model=WorkflowExecutionResponse,
    dependencies=[_ANALYST],
)
async def reject_workflow_step(
    execution_id: str,
    body: RejectWorkflowStepRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowExecutionResponse:
    from application.operating_system.playbook_service import reject_workflow_step
    row = await reject_workflow_step(
        organization_id=current_user.organization_id,
        execution_id=execution_id,
        rejected_by=current_user.id,
        reason=body.reason,
        session=session,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    return WorkflowExecutionResponse(**row)


# ── Strategic Risks ───────────────────────────────────────────────────────────

@router.get(
    "/strategic-risks",
    response_model=list[StrategicRiskResponse],
    dependencies=[_ANALYST],
)
async def list_strategic_risks(
    risk_level: str | None = None,
    risk_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[StrategicRiskResponse]:
    from application.operating_system.strategic_risk_service import list_strategic_risks
    rows = await list_strategic_risks(
        current_user.organization_id, session,
        risk_level=risk_level, risk_status=risk_status, limit=limit,
    )
    return [StrategicRiskResponse(**r) for r in rows]


@router.post(
    "/strategic-risks",
    response_model=StrategicRiskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_strategic_risk(
    body: CreateStrategicRiskRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> StrategicRiskResponse:
    from application.operating_system.strategic_risk_service import create_strategic_risk
    row = await create_strategic_risk(
        organization_id=current_user.organization_id,
        title=body.title,
        category=body.category,
        description=body.description,
        risk_level=body.risk_level,
        probability=body.probability,
        impact=body.impact,
        owner_user_id=body.owner_user_id,
        linked_suppliers=body.linked_suppliers,
        linked_objectives=body.linked_objectives,
        linked_initiatives=body.linked_initiatives,
        linked_compliance_programs=body.linked_compliance_programs,
        session=session,
    )
    return StrategicRiskResponse(**row)


@router.get(
    "/strategic-risks/{risk_id}",
    response_model=StrategicRiskResponse,
    dependencies=[_ANALYST],
)
async def get_strategic_risk(
    risk_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> StrategicRiskResponse:
    from application.operating_system.strategic_risk_service import get_strategic_risk
    row = await get_strategic_risk(current_user.organization_id, risk_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategic risk not found")
    return StrategicRiskResponse(**row)


@router.patch(
    "/strategic-risks/{risk_id}",
    response_model=StrategicRiskResponse,
    dependencies=[_ANALYST],
)
async def update_strategic_risk(
    risk_id: str,
    body: UpdateStrategicRiskRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> StrategicRiskResponse:
    from application.operating_system.strategic_risk_service import update_strategic_risk
    row = await update_strategic_risk(
        current_user.organization_id, risk_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Strategic risk not found")
    return StrategicRiskResponse(**row)


# ── ESG Health Score ──────────────────────────────────────────────────────────

@router.get(
    "/health-score",
    response_model=ESGHealthScoreResponse,
    dependencies=[_ANALYST],
)
async def get_health_score(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGHealthScoreResponse:
    from application.operating_system.health_score_service import get_latest_health_score
    row = await get_latest_health_score(current_user.organization_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="No health score computed yet")
    return ESGHealthScoreResponse(**row)


@router.post(
    "/health-score/refresh",
    response_model=ESGHealthScoreResponse,
    dependencies=[_ADMIN],
)
async def refresh_health_score(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGHealthScoreResponse:
    from application.operating_system.health_score_service import compute_health_score
    row = await compute_health_score(current_user.organization_id, session)
    return ESGHealthScoreResponse(**row)


# ── Escalation Rules ──────────────────────────────────────────────────────────

@router.get(
    "/escalation-rules",
    response_model=list[EscalationRuleResponse],
    dependencies=[_ADMIN],
)
async def list_escalation_rules(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[EscalationRuleResponse]:
    from application.operating_system.escalation_service import list_escalation_rules
    rows = await list_escalation_rules(current_user.organization_id, session)
    return [EscalationRuleResponse(**r) for r in rows]


@router.post(
    "/escalation-rules",
    response_model=EscalationRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_escalation_rule(
    body: CreateEscalationRuleRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EscalationRuleResponse:
    from application.operating_system.escalation_service import create_escalation_rule
    row = await create_escalation_rule(
        organization_id=current_user.organization_id,
        rule_name=body.rule_name,
        condition_entity_type=body.condition_entity_type,
        condition_status=body.condition_status,
        escalate_to_role=body.escalate_to_role,
        condition_overdue_days=body.condition_overdue_days,
        condition_priority=body.condition_priority,
        escalate_to_user_id=body.escalate_to_user_id,
        notification_message=body.notification_message,
        session=session,
    )
    return EscalationRuleResponse(**row)


@router.post(
    "/escalation-rules/evaluate",
    response_model=list[EscalationTriggeredResponse],
    dependencies=[_ANALYST],
)
async def evaluate_escalations(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[EscalationTriggeredResponse]:
    from application.operating_system.escalation_service import evaluate_escalations
    rows = await evaluate_escalations(current_user.organization_id, session)
    return [EscalationTriggeredResponse(**r) for r in rows]


# ── Operating System Dashboard ────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=OperatingSystemDashboard,
    dependencies=[_ANALYST],
)
async def get_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OperatingSystemDashboard:
    from sqlalchemy import func, select
    from datetime import UTC, datetime
    from infrastructure.persistence.models.operating_system import (
        ESGObjectiveModel, ESGInitiativeModel, ESGActionModel, StrategicRiskModel,
    )
    from application.operating_system.action_service import list_actions
    from application.operating_system.strategic_risk_service import list_strategic_risks
    from application.operating_system.health_score_service import get_latest_health_score
    from application.operating_system.escalation_service import evaluate_escalations

    org = current_user.organization_id
    now = datetime.now(UTC)

    # Objective counts
    obj_total = (await session.execute(
        select(func.count()).select_from(ESGObjectiveModel)
        .where(ESGObjectiveModel.organization_id == org)
    )).scalar_one()

    obj_at_risk = (await session.execute(
        select(func.count()).select_from(ESGObjectiveModel).where(
            ESGObjectiveModel.organization_id == org,
            ESGObjectiveModel.objective_status.in_(["AT_RISK", "OFF_TRACK"]),
        )
    )).scalar_one()

    # Objective status breakdown
    status_rows = (await session.execute(
        select(ESGObjectiveModel.objective_status, func.count())
        .where(ESGObjectiveModel.organization_id == org)
        .group_by(ESGObjectiveModel.objective_status)
    )).all()
    objectives_by_status = {row[0]: row[1] for row in status_rows}

    # Initiative counts
    init_total = (await session.execute(
        select(func.count()).select_from(ESGInitiativeModel)
        .where(ESGInitiativeModel.organization_id == org)
    )).scalar_one()

    init_active = (await session.execute(
        select(func.count()).select_from(ESGInitiativeModel).where(
            ESGInitiativeModel.organization_id == org,
            ESGInitiativeModel.initiative_status == "ACTIVE",
        )
    )).scalar_one()

    # Action counts
    actions_open = (await session.execute(
        select(func.count()).select_from(ESGActionModel).where(
            ESGActionModel.organization_id == org,
            ESGActionModel.action_status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"]),
        )
    )).scalar_one()

    actions_overdue = (await session.execute(
        select(func.count()).select_from(ESGActionModel).where(
            ESGActionModel.organization_id == org,
            ESGActionModel.due_date < now,
            ESGActionModel.action_status.in_(["OPEN", "IN_PROGRESS", "BLOCKED"]),
        )
    )).scalar_one()

    # Strategic risks: critical count
    critical_risks = (await session.execute(
        select(func.count()).select_from(StrategicRiskModel).where(
            StrategicRiskModel.organization_id == org,
            StrategicRiskModel.risk_level == "CRITICAL",
            StrategicRiskModel.risk_status != "CLOSED",
        )
    )).scalar_one()

    # Top overdue actions (max 5)
    overdue_actions = await list_actions(org, session, overdue_only=True, limit=5)

    # Recent critical strategic risks
    recent_risks = await list_strategic_risks(
        org, session, risk_level="CRITICAL", limit=5
    )

    # Health score
    health = await get_latest_health_score(org, session)
    health_score = health["overall_score"] if health else None

    # Escalations
    escalations = await evaluate_escalations(org, session)

    from infrastructure.persistence.models.operating_system import (
        ComplianceOperationModel, GovernanceCalendarEventModel,
        ESGProgramModel, ESGControlModel,
    )

    compliance_ops_count = (await session.execute(
        select(func.count()).select_from(ComplianceOperationModel)
        .where(ComplianceOperationModel.organization_id == org)
    )).scalar_one()

    calendar_events_count = (await session.execute(
        select(func.count()).select_from(GovernanceCalendarEventModel)
        .where(GovernanceCalendarEventModel.organization_id == org,
               GovernanceCalendarEventModel.event_status == "SCHEDULED")
    )).scalar_one()

    programs_total = (await session.execute(
        select(func.count()).select_from(ESGProgramModel)
        .where(ESGProgramModel.organization_id == org)
    )).scalar_one()

    controls_total = (await session.execute(
        select(func.count()).select_from(ESGControlModel)
        .where(ESGControlModel.organization_id == org)
    )).scalar_one()

    return OperatingSystemDashboard(
        objectives_total=obj_total,
        objectives_at_risk=obj_at_risk,
        initiatives_total=init_total,
        initiatives_active=init_active,
        actions_open=actions_open,
        actions_overdue=actions_overdue,
        escalations_triggered=len(escalations),
        strategic_risks_critical=critical_risks,
        latest_health_score=health_score,
        top_overdue_actions=[ESGActionResponse(**a) for a in overdue_actions],
        objectives_by_status=objectives_by_status,
        recent_strategic_risks=[StrategicRiskResponse(**r) for r in recent_risks],
        compliance_operations=compliance_ops_count,
        governance_calendar_events=calendar_events_count,
        programs_total=programs_total,
        controls_total=controls_total,
    )


# ── Governance Calendar ───────────────────────────────────────────────────────

@router.get(
    "/calendar",
    response_model=list[CalendarEventResponse],
    dependencies=[_ANALYST],
)
async def list_calendar_events(
    event_type: str | None = None,
    event_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CalendarEventResponse]:
    from application.operating_system.calendar_service import list_events
    rows = await list_events(
        current_user.organization_id, session,
        event_type=event_type, event_status=event_status, limit=limit,
    )
    return [CalendarEventResponse(**r) for r in rows]


@router.post(
    "/calendar",
    response_model=CalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_calendar_event(
    body: CreateCalendarEventRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalendarEventResponse:
    from application.operating_system.calendar_service import create_event
    row = await create_event(
        organization_id=current_user.organization_id,
        title=body.title, event_type=body.event_type,
        scheduled_at=body.scheduled_at, recurrence_rule=body.recurrence_rule,
        reminder_days=body.reminder_days, linked_entity_type=body.linked_entity_type,
        linked_entity_id=body.linked_entity_id, notes=body.notes,
        session=session,
    )
    return CalendarEventResponse(**row)


@router.get(
    "/calendar/{event_id}",
    response_model=CalendarEventResponse,
    dependencies=[_ANALYST],
)
async def get_calendar_event(
    event_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalendarEventResponse:
    from application.operating_system.calendar_service import get_event
    row = await get_event(current_user.organization_id, event_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return CalendarEventResponse(**row)


@router.patch(
    "/calendar/{event_id}",
    response_model=CalendarEventResponse,
    dependencies=[_ANALYST],
)
async def update_calendar_event(
    event_id: str,
    body: UpdateCalendarEventRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalendarEventResponse:
    from application.operating_system.calendar_service import update_event
    row = await update_event(
        current_user.organization_id, event_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return CalendarEventResponse(**row)


@router.delete(
    "/calendar/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ANALYST],
)
async def delete_calendar_event(
    event_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    from application.operating_system.calendar_service import delete_event
    deleted = await delete_event(current_user.organization_id, event_id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="Calendar event not found")


# ── Programs ──────────────────────────────────────────────────────────────────

@router.get(
    "/programs",
    response_model=list[ESGProgramResponse],
    dependencies=[_ANALYST],
)
async def list_programs(
    program_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGProgramResponse]:
    from application.operating_system.program_service import list_programs
    rows = await list_programs(
        current_user.organization_id, session,
        program_status=program_status, limit=limit,
    )
    return [ESGProgramResponse(**r) for r in rows]


@router.post(
    "/programs",
    response_model=ESGProgramResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_program(
    body: CreateProgramRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGProgramResponse:
    from application.operating_system.program_service import create_program
    row = await create_program(
        organization_id=current_user.organization_id,
        title=body.title, description=body.description,
        linked_objectives=body.linked_objectives,
        linked_initiatives=body.linked_initiatives,
        linked_suppliers=body.linked_suppliers,
        session=session,
    )
    return ESGProgramResponse(**row)


@router.get(
    "/programs/{program_id}",
    response_model=ESGProgramResponse,
    dependencies=[_ANALYST],
)
async def get_program(
    program_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGProgramResponse:
    from application.operating_system.program_service import get_program
    row = await get_program(current_user.organization_id, program_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return ESGProgramResponse(**row)


@router.patch(
    "/programs/{program_id}",
    response_model=ESGProgramResponse,
    dependencies=[_ANALYST],
)
async def update_program(
    program_id: str,
    body: UpdateProgramRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGProgramResponse:
    from application.operating_system.program_service import update_program
    row = await update_program(
        current_user.organization_id, program_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return ESGProgramResponse(**row)


# ── Controls ──────────────────────────────────────────────────────────────────

@router.get(
    "/controls",
    response_model=list[ESGControlResponse],
    dependencies=[_ANALYST],
)
async def list_controls(
    control_type: str | None = None,
    effectiveness_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ESGControlResponse]:
    from application.operating_system.control_service import list_controls
    rows = await list_controls(
        current_user.organization_id, session,
        control_type=control_type, effectiveness_status=effectiveness_status, limit=limit,
    )
    return [ESGControlResponse(**r) for r in rows]


@router.post(
    "/controls",
    response_model=ESGControlResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_control(
    body: CreateControlRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGControlResponse:
    from application.operating_system.control_service import create_control
    row = await create_control(
        organization_id=current_user.organization_id,
        control_name=body.control_name, control_type=body.control_type,
        owner_user_id=body.owner_user_id, frequency=body.frequency,
        evidence_required=body.evidence_required,
        session=session,
    )
    return ESGControlResponse(**row)


@router.get(
    "/controls/{control_id}",
    response_model=ESGControlResponse,
    dependencies=[_ANALYST],
)
async def get_control(
    control_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGControlResponse:
    from application.operating_system.control_service import get_control
    row = await get_control(current_user.organization_id, control_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Control not found")
    return ESGControlResponse(**row)


@router.patch(
    "/controls/{control_id}",
    response_model=ESGControlResponse,
    dependencies=[_ANALYST],
)
async def update_control(
    control_id: str,
    body: UpdateControlRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ESGControlResponse:
    from application.operating_system.control_service import update_control
    row = await update_control(
        current_user.organization_id, control_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Control not found")
    return ESGControlResponse(**row)


# ── Control Tests ─────────────────────────────────────────────────────────────

@router.get(
    "/tests",
    response_model=list[ControlTestResponse],
    dependencies=[_ANALYST],
)
async def list_control_tests(
    control_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ControlTestResponse]:
    from application.operating_system.control_test_service import list_tests
    rows = await list_tests(
        current_user.organization_id, session,
        control_id=control_id, limit=limit,
    )
    return [ControlTestResponse(**r) for r in rows]


@router.post(
    "/tests",
    response_model=ControlTestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_control_test(
    body: CreateControlTestRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlTestResponse:
    from application.operating_system.control_test_service import create_test
    row = await create_test(
        organization_id=current_user.organization_id,
        control_id=body.control_id, test_result=body.test_result,
        tested_at=body.tested_at, performed_by=body.performed_by,
        findings=body.findings, session=session,
    )
    return ControlTestResponse(**row)


@router.patch(
    "/tests/{test_id}",
    response_model=ControlTestResponse,
    dependencies=[_ANALYST],
)
async def update_control_test(
    test_id: str,
    body: UpdateControlTestRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ControlTestResponse:
    from application.operating_system.control_test_service import update_test
    row = await update_test(
        current_user.organization_id, test_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Control test not found")
    return ControlTestResponse(**row)


@router.delete(
    "/tests/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ANALYST],
)
async def delete_control_test(
    test_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    from application.operating_system.control_test_service import delete_test
    deleted = await delete_test(current_user.organization_id, test_id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="Control test not found")


# ── Compliance Operations ─────────────────────────────────────────────────────

@router.get(
    "/compliance-operations",
    response_model=list[ComplianceOperationResponse],
    dependencies=[_ANALYST],
)
async def list_compliance_operations(
    framework_name: str | None = None,
    operation_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ComplianceOperationResponse]:
    from application.operating_system.compliance_operation_service import list_compliance_operations
    rows = await list_compliance_operations(
        current_user.organization_id, session,
        framework_name=framework_name, operation_status=operation_status, limit=limit,
    )
    return [ComplianceOperationResponse(**r) for r in rows]


@router.post(
    "/compliance-operations",
    response_model=ComplianceOperationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_compliance_operation(
    body: CreateComplianceOperationRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ComplianceOperationResponse:
    from application.operating_system.compliance_operation_service import create_compliance_operation
    row = await create_compliance_operation(
        organization_id=current_user.organization_id,
        framework_name=body.framework_name, owner_user_id=body.owner_user_id,
        coverage_percent=body.coverage_percent, gap_count=body.gap_count,
        session=session,
    )
    return ComplianceOperationResponse(**row)


@router.get(
    "/compliance-operations/{operation_id}",
    response_model=ComplianceOperationResponse,
    dependencies=[_ANALYST],
)
async def get_compliance_operation(
    operation_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ComplianceOperationResponse:
    from application.operating_system.compliance_operation_service import get_compliance_operation
    row = await get_compliance_operation(current_user.organization_id, operation_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance operation not found")
    return ComplianceOperationResponse(**row)


@router.patch(
    "/compliance-operations/{operation_id}",
    response_model=ComplianceOperationResponse,
    dependencies=[_ANALYST],
)
async def update_compliance_operation(
    operation_id: str,
    body: UpdateComplianceOperationRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ComplianceOperationResponse:
    from application.operating_system.compliance_operation_service import update_compliance_operation
    row = await update_compliance_operation(
        current_user.organization_id, operation_id, session,
        **body.model_dump(exclude_none=True),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Compliance operation not found")
    return ComplianceOperationResponse(**row)


# ── Accountability ────────────────────────────────────────────────────────────

@router.get(
    "/accountability",
    response_model=list[AccountabilityAssignmentResponse],
    dependencies=[_ANALYST],
)
async def list_accountability(
    entity_type: str | None = None,
    entity_id: str | None = None,
    role: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AccountabilityAssignmentResponse]:
    from application.operating_system.accountability_service import list_assignments
    rows = await list_assignments(
        current_user.organization_id, session,
        entity_type=entity_type, entity_id=entity_id, role=role, limit=limit,
    )
    return [AccountabilityAssignmentResponse(**r) for r in rows]


@router.post(
    "/accountability",
    response_model=AccountabilityAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def assign_accountability(
    body: AssignAccountabilityRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AccountabilityAssignmentResponse:
    from application.operating_system.accountability_service import assign_accountability
    row = await assign_accountability(
        organization_id=current_user.organization_id,
        entity_type=body.entity_type, entity_id=body.entity_id,
        role=body.role, assigned_to_user_id=body.assigned_to_user_id,
        assigned_by_user_id=body.assigned_by_user_id,
        session=session,
    )
    return AccountabilityAssignmentResponse(**row)


@router.get(
    "/accountability/{assignment_id}",
    response_model=AccountabilityAssignmentResponse,
    dependencies=[_ANALYST],
)
async def get_accountability(
    assignment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AccountabilityAssignmentResponse:
    from application.operating_system.accountability_service import get_assignment
    row = await get_assignment(current_user.organization_id, assignment_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return AccountabilityAssignmentResponse(**row)


@router.delete(
    "/accountability/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ANALYST],
)
async def remove_accountability(
    assignment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    from application.operating_system.accountability_service import remove_assignment
    removed = await remove_assignment(current_user.organization_id, assignment_id, session)
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get(
    "/timeline",
    response_model=list[TimelineEntry],
    dependencies=[_ANALYST],
)
async def get_timeline(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[TimelineEntry]:
    """Chronological feed aggregating all M39 entities for the org.

    Fetches a buffer (limit*5) from each source, merges all, sorts globally by
    timestamp desc, then takes the top `limit`. This avoids per-source truncation
    hiding older events from low-volume sources.
    """
    from infrastructure.persistence.models.operating_system import (
        ESGObjectiveModel, ESGActionModel,
        WorkflowExecutionModel, StrategicRiskModel, ComplianceOperationModel,
        GovernanceCalendarEventModel,
    )
    org = current_user.organization_id
    buffer = min(limit * 5, 1000)
    all_entries: list[TimelineEntry] = []

    async def _fetch(model, label, entity_type, title_col, ts_col, status_col=None):
        stmt = (
            select(model)
            .where(model.organization_id == org)
            .order_by(getattr(model, ts_col).desc())
            .limit(buffer)
        )
        rows = (await session.execute(stmt)).scalars().all()
        for r in rows:
            ts = getattr(r, ts_col, None) or getattr(r, "created_at")
            all_entries.append(TimelineEntry(
                event_type=label,
                entity_type=entity_type,
                entity_id=r.id,
                title=getattr(r, title_col, ""),
                timestamp=ts,
                status=getattr(r, status_col, None) if status_col else None,
            ))

    await _fetch(ESGObjectiveModel, "objective.created", "ESGObjective",
                 "title", "created_at", "objective_status")
    await _fetch(ESGActionModel, "action.created", "ESGAction",
                 "title", "created_at", "action_status")
    await _fetch(WorkflowExecutionModel, "workflow.started", "WorkflowExecution",
                 "workflow_type", "created_at", "execution_status")
    await _fetch(StrategicRiskModel, "strategic_risk.identified", "StrategicRisk",
                 "title", "created_at", "risk_status")
    await _fetch(ComplianceOperationModel, "compliance_op.synced", "ComplianceOperation",
                 "framework_name", "created_at", "operation_status")
    await _fetch(GovernanceCalendarEventModel, "calendar.event_created", "GovernanceCalendarEvent",
                 "title", "scheduled_at", "event_status")

    all_entries.sort(key=lambda e: e.timestamp, reverse=True)
    return all_entries[:limit]
