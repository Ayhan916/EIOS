"""M36 Agent Monitoring API Router.

Prefix: /api/v1/agents

Scopes:
  agent:read  — read agents, findings, alerts, runs, drafts
  agent:write — trigger runs, acknowledge findings/alerts, approve/reject drafts,
                manage escalation rules

All reads scoped to current_user.organization_id.
Agents may NEVER approve findings, close risks, or make irreversible decisions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst
from interfaces.api.schemas.agent_monitoring import (
    AcknowledgeAlertRequest,
    AcknowledgeFindingRequest,
    AgentAlertResponse,
    AgentDashboard,
    AgentFindingResponse,
    AgentHealthInfo,
    AgentRunResponse,
    ApproveDraftRequest,
    EscalationRuleCreate,
    EscalationRuleResponse,
    MonitoringAgentResponse,
    RecommendationDraftResponse,
    RejectDraftRequest,
    TriggerAgentRunRequest,
)

router = APIRouter(prefix="/agents", tags=["Agent Monitoring (M36)"])

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)


# ── Agent Registry ────────────────────────────────────────────────────────────

@router.get("", response_model=list[MonitoringAgentResponse], dependencies=[_ANALYST])
async def list_agents(
    session: AsyncSession = Depends(get_db),
) -> list[MonitoringAgentResponse]:
    from application.agent_monitoring.agent_service import list_agents

    agents = await list_agents(session)
    return [MonitoringAgentResponse.model_validate(a) for a in agents]


@router.patch(
    "/{agent_id}/enable",
    response_model=MonitoringAgentResponse,
    dependencies=[_ADMIN],
)
async def set_agent_enabled(
    agent_id: str,
    enabled: bool = Query(...),
    session: AsyncSession = Depends(get_db),
) -> MonitoringAgentResponse:
    from application.agent_monitoring.agent_service import set_agent_enabled

    agent = await set_agent_enabled(agent_id, enabled, session)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    return MonitoringAgentResponse.model_validate(agent)


# ── Manual Trigger ─────────────────────────────────────────────────────────────

@router.post(
    "/trigger",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def trigger_agent_run(
    body: TriggerAgentRunRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentRunResponse:
    from application.agent_monitoring.scheduler import trigger_agent_run

    org_id = current_user.organization_id  # F1: always scoped to caller's org
    try:
        run = await trigger_agent_run(body.agent_type, org_id, session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AgentRunResponse.model_validate(run)


# ── Run History ────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=list[AgentRunResponse], dependencies=[_ANALYST])
async def list_runs(
    agent_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AgentRunResponse]:
    from application.agent_monitoring.agent_service import list_runs

    runs = await list_runs(
        agent_id=agent_id,
        organization_id=current_user.organization_id,
        limit=limit,
        session=session,
    )
    return [AgentRunResponse.model_validate(r) for r in runs]


# ── Findings ──────────────────────────────────────────────────────────────────

@router.get("/findings", response_model=list[AgentFindingResponse], dependencies=[_ANALYST])
async def list_findings(
    supplier_id: str | None = None,
    agent_id: str | None = None,
    finding_status: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AgentFindingResponse]:
    from application.agent_monitoring.finding_service import list_findings

    rows = await list_findings(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        agent_id=agent_id,
        finding_status=finding_status,
        severity=severity,
        limit=limit,
        offset=offset,
        session=session,
    )
    return [AgentFindingResponse.model_validate(r) for r in rows]


@router.get("/findings/{finding_id}", response_model=AgentFindingResponse, dependencies=[_ANALYST])
async def get_finding(
    finding_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentFindingResponse:
    from application.agent_monitoring.finding_service import get_finding

    finding = await get_finding(finding_id, current_user.organization_id, session)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return AgentFindingResponse.model_validate(finding)


@router.post(
    "/findings/{finding_id}/acknowledge",
    response_model=AgentFindingResponse,
    dependencies=[_ANALYST],
)
async def acknowledge_finding(
    finding_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentFindingResponse:
    from application.agent_monitoring.finding_service import acknowledge_finding

    try:
        finding = await acknowledge_finding(
            finding_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AgentFindingResponse.model_validate(finding)


@router.post(
    "/findings/{finding_id}/dismiss",
    response_model=AgentFindingResponse,
    dependencies=[_ANALYST],
)
async def dismiss_finding(
    finding_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentFindingResponse:
    from application.agent_monitoring.finding_service import dismiss_finding

    try:
        finding = await dismiss_finding(
            finding_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AgentFindingResponse.model_validate(finding)


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AgentAlertResponse], dependencies=[_ANALYST])
async def list_alerts(
    supplier_id: str | None = None,
    severity: str | None = None,
    unacknowledged_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AgentAlertResponse]:
    from application.agent_monitoring.alert_service import list_alerts

    rows = await list_alerts(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        severity=severity,
        unacknowledged_only=unacknowledged_only,
        limit=limit,
        session=session,
    )
    return [AgentAlertResponse.model_validate(r) for r in rows]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AgentAlertResponse,
    dependencies=[_ANALYST],
)
async def acknowledge_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentAlertResponse:
    from application.agent_monitoring.alert_service import acknowledge_alert

    try:
        alert = await acknowledge_alert(
            alert_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AgentAlertResponse.model_validate(alert)


# ── Escalation Rules ──────────────────────────────────────────────────────────

@router.get(
    "/escalation-rules",
    response_model=list[EscalationRuleResponse],
    dependencies=[_ANALYST],
)
async def list_escalation_rules(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[EscalationRuleResponse]:
    from application.agent_monitoring.alert_service import list_escalation_rules

    rows = await list_escalation_rules(current_user.organization_id, session)
    return [EscalationRuleResponse.model_validate(r) for r in rows]


@router.post(
    "/escalation-rules",
    response_model=EscalationRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_escalation_rule(
    body: EscalationRuleCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EscalationRuleResponse:
    from application.agent_monitoring.alert_service import create_escalation_rule

    rule = await create_escalation_rule(
        organization_id=current_user.organization_id,
        name=body.name,
        description=body.description,
        condition_json=body.condition_json,
        escalation_severity=body.escalation_severity,
        created_by=current_user.id,
        agent_type=body.agent_type,
        session=session,
    )
    await session.commit()
    return EscalationRuleResponse.model_validate(rule)


# ── Recommendation Drafts ─────────────────────────────────────────────────────

@router.get(
    "/drafts",
    response_model=list[RecommendationDraftResponse],
    dependencies=[_ANALYST],
)
async def list_drafts(
    draft_status: str | None = None,
    supplier_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RecommendationDraftResponse]:
    from application.agent_monitoring.alert_service import list_recommendation_drafts

    rows = await list_recommendation_drafts(
        organization_id=current_user.organization_id,
        draft_status=draft_status,
        supplier_id=supplier_id,
        limit=limit,
        session=session,
    )
    return [RecommendationDraftResponse.model_validate(r) for r in rows]


@router.post(
    "/drafts/{draft_id}/approve",
    response_model=RecommendationDraftResponse,
    dependencies=[_ADMIN],
)
async def approve_draft(
    draft_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecommendationDraftResponse:
    from application.agent_monitoring.alert_service import approve_draft

    try:
        draft = await approve_draft(draft_id, current_user.organization_id, current_user.id, session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RecommendationDraftResponse.model_validate(draft)


@router.post(
    "/drafts/{draft_id}/reject",
    response_model=RecommendationDraftResponse,
    dependencies=[_ANALYST],
)
async def reject_draft(
    draft_id: str,
    body: RejectDraftRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecommendationDraftResponse:
    from application.agent_monitoring.alert_service import reject_draft

    try:
        draft = await reject_draft(
            draft_id, current_user.organization_id, current_user.id, body.reason, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RecommendationDraftResponse.model_validate(draft)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=AgentDashboard, dependencies=[_ANALYST])
async def get_agent_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AgentDashboard:
    from application.agent_monitoring.agent_service import list_agents
    from application.agent_monitoring.alert_service import list_alerts
    from application.agent_monitoring.finding_service import list_findings
    from infrastructure.persistence.models.agent_monitoring import (
        AgentAlertModel,
        AgentFindingModel,
        RecommendationDraftModel,
    )
    from sqlalchemy import func, select

    org_id = current_user.organization_id

    agents = await list_agents(session)
    active = sum(1 for a in agents if a.status == "ACTIVE" and a.enabled)
    paused = sum(1 for a in agents if a.status == "PAUSED" or not a.enabled)
    failed = sum(1 for a in agents if a.status == "FAILED")

    open_findings = (await session.execute(
        select(func.count()).select_from(AgentFindingModel).where(
            AgentFindingModel.organization_id == org_id,
            AgentFindingModel.finding_status == "OPEN",
        )
    )).scalar_one()

    unacked_alerts = (await session.execute(
        select(func.count()).select_from(AgentAlertModel).where(
            AgentAlertModel.organization_id == org_id,
            AgentAlertModel.acknowledged_at.is_(None),
        )
    )).scalar_one()

    critical_alerts = (await session.execute(
        select(func.count()).select_from(AgentAlertModel).where(
            AgentAlertModel.organization_id == org_id,
            AgentAlertModel.severity == "CRITICAL",
            AgentAlertModel.acknowledged_at.is_(None),
        )
    )).scalar_one()

    pending_drafts = (await session.execute(
        select(func.count()).select_from(RecommendationDraftModel).where(
            RecommendationDraftModel.organization_id == org_id,
            RecommendationDraftModel.draft_status == "PENDING",
        )
    )).scalar_one()

    recent_findings = await list_findings(org_id, limit=10, session=session)
    recent_alerts = await list_alerts(org_id, limit=10, session=session)

    from application.agent_monitoring.agent_service import get_agent_health_list
    health_list = await get_agent_health_list(session)
    per_agent_health = [AgentHealthInfo(**h) for h in health_list]

    return AgentDashboard(
        active_agents=active,
        paused_agents=paused,
        failed_agents=failed,
        total_open_findings=open_findings,
        total_unacknowledged_alerts=unacked_alerts,
        total_critical_alerts=critical_alerts,
        total_pending_drafts=pending_drafts,
        recent_findings=[AgentFindingResponse.model_validate(f) for f in recent_findings],
        recent_alerts=[AgentAlertResponse.model_validate(a) for a in recent_alerts],
        per_agent_health=per_agent_health,
    )
