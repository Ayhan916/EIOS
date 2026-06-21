"""M41 — AI Governance Router (/api/v1/ai-governance).

Auth: every endpoint requires a valid JWT Bearer token.
Actor attribution: current_user.id (from JWT sub claim) is passed to all services.
Tenant isolation: organization_id ownership is validated at the service layer.
"""

from __future__ import annotations

from datetime import datetime, timezone

import jwt as _jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.ai_governance import (
    assurance_service,
    control_service,
    decision_service,
    incident_service,
    inventory_service,
    monitoring_service,
    prompt_service,
)
from application.ai_governance.inventory_service import AIGovernanceConflict, AIGovernanceError
from interfaces.api.deps import get_db
from interfaces.api.schemas.ai_governance import (
    AIControlCreate,
    AIControlResponse,
    AIGovernanceDashboard,
    AIIncidentCreate,
    AIIncidentResolve,
    AIIncidentResponse,
    AIModelCreate,
    AIModelResponse,
    AIModelStatusUpdate,
    AIPolicyCreate,
    AIPolicyResponse,
    AIUseCaseCreate,
    AIUseCaseResponse,
    AssuranceReportCreate,
    AssuranceReportResponse,
    ControlTestCreate,
    ControlTestResponse,
    DecisionLogCreate,
    DecisionLogResponse,
    DriftAlertResponse,
    ExplanationCreate,
    ExplanationResponse,
    HumanReviewCreate,
    HumanReviewResponse,
    MonitoringSnapshotCreate,
    MonitoringSnapshotResponse,
    PromptChangeResponse,
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateRevise,
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    RegulationMappingCreate,
    RegulationMappingHistoryResponse,
    RegulationMappingResponse,
    RegulationMappingStatusUpdate,
    WorkflowStageAdvance,
    WorkflowStageResponse,
)
from shared.security import decode_token

router = APIRouter(prefix="/ai-governance", tags=["ai-governance"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_actor(request: Request) -> str:
    """Extract actor ID from JWT Bearer token.

    Synchronous dependency — reads the Authorization header directly.
    Returns the 'sub' claim (user ID) for attribution in all governance records.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[7:]
    try:
        payload = decode_token(token)
    except _jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except _jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return sub


def _gov_error(exc: AIGovernanceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _gov_conflict(exc: AIGovernanceConflict) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/{organization_id}/dashboard", response_model=AIGovernanceDashboard)
async def get_dashboard(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    from infrastructure.persistence.models.ai_governance import (
        AIModelModel,
        ModelDriftAlertModel,
        AIAssuranceReportModel,
        AIPolicyModel,
    )

    stats = await db.run_sync(
        lambda s: assurance_service.get_dashboard_stats(organization_id, s)
    )

    # Remaining counts that aren't in the consolidated query
    def _extra_counts(s):
        from sqlalchemy.orm import Session as _S

        unresolved_drift = (
            s.query(ModelDriftAlertModel)
            .join(AIModelModel, AIModelModel.id == ModelDriftAlertModel.model_id)
            .filter(
                AIModelModel.organization_id == organization_id,
                ModelDriftAlertModel.is_resolved == False,  # noqa: E712
            )
            .count()
        )
        active_policies = (
            s.query(AIPolicyModel)
            .filter(
                AIPolicyModel.organization_id == organization_id,
                AIPolicyModel.is_active == True,  # noqa: E712
            )
            .count()
        )
        last_report = (
            s.query(AIAssuranceReportModel)
            .filter(AIAssuranceReportModel.organization_id == organization_id)
            .order_by(AIAssuranceReportModel.created_at.desc())
            .first()
        )
        return unresolved_drift, active_policies, last_report

    unresolved_drift, active_policies, last_report = await db.run_sync(_extra_counts)

    return AIGovernanceDashboard(
        organization_id=organization_id,
        total_models=stats["total_models"],
        active_models=stats["active_models"],
        draft_models=stats["draft_models"],
        total_use_cases=stats["total_use_cases"],
        pending_approvals=stats["pending_approvals"],
        open_incidents=stats["open_incidents"],
        unresolved_drift_alerts=unresolved_drift,
        active_policies=active_policies,
        last_report_status=last_report.overall_status if last_report else None,
    )


# ── AI Models ─────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/models",
    response_model=AIModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_model(
    organization_id: str,
    body: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        m = await db.run_sync(
            lambda s: inventory_service.register_ai_model(
                organization_id=organization_id,
                name=body.name,
                provider=body.provider,
                model_type=body.model_type,
                actor_id=actor_id,
                session=s,
                model_version=body.model_version,
                purpose=body.purpose,
                owner_user_id=body.owner_user_id,
                metadata_=body.metadata_,
            )
        )
        await db.refresh(m)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return m


@router.get("/{organization_id}/models", response_model=list[AIModelResponse])
async def list_models(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: inventory_service.list_ai_models(organization_id, s, limit=limit, offset=offset)
    )


@router.get("/{organization_id}/models/{model_id}", response_model=AIModelResponse)
async def get_model(
    organization_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    m = await db.run_sync(lambda s: inventory_service.get_ai_model(model_id, s))
    if not m or m.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="AI model not found")
    return m


@router.patch("/{organization_id}/models/{model_id}/status", response_model=AIModelResponse)
async def update_model_status(
    organization_id: str,
    model_id: str,
    body: AIModelStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        m = await db.run_sync(
            lambda s: inventory_service.update_ai_model_status(
                model_id, body.ai_status, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(m)
    except AIGovernanceConflict as exc:
        raise _gov_conflict(exc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return m


# ── Approval Workflow ─────────────────────────────────────────────────────────

@router.get(
    "/{organization_id}/models/{model_id}/workflow",
    response_model=list[WorkflowStageResponse],
)
async def get_workflow(
    organization_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: inventory_service.get_workflow_stages(model_id, s)
    )


@router.post(
    "/{organization_id}/models/{model_id}/workflow/advance",
    response_model=WorkflowStageResponse,
)
async def advance_workflow(
    organization_id: str,
    model_id: str,
    body: WorkflowStageAdvance,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        wf = await db.run_sync(
            lambda s: inventory_service.advance_approval_stage(
                model_id=model_id,
                stage=body.stage,
                actor_id=actor_id,
                session=s,
                organization_id=organization_id,
                approved=body.approved,
                notes=body.notes,
            )
        )
        await db.refresh(wf)
    except AIGovernanceConflict as exc:
        raise _gov_conflict(exc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return wf


# ── Use Cases ─────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/models/{model_id}/use-cases",
    response_model=AIUseCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_use_case(
    organization_id: str,
    model_id: str,
    body: AIUseCaseCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        uc = await db.run_sync(
            lambda s: inventory_service.register_use_case(
                model_id=model_id,
                organization_id=organization_id,
                title=body.title,
                actor_id=actor_id,
                session=s,
                description=body.description,
                business_owner=body.business_owner,
                technical_owner=body.technical_owner,
                risk_level=body.risk_level,
            )
        )
        await db.refresh(uc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return uc


@router.get(
    "/{organization_id}/models/{model_id}/use-cases",
    response_model=list[AIUseCaseResponse],
)
async def list_use_cases(
    organization_id: str,
    model_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: inventory_service.list_use_cases(model_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/use-cases/{use_case_id}/approve",
    response_model=AIUseCaseResponse,
)
async def approve_use_case(
    organization_id: str,
    use_case_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        uc = await db.run_sync(
            lambda s: inventory_service.approve_use_case(
                use_case_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(uc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return uc


# ── Risk Assessments ──────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/models/{model_id}/risk-assessments",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_assessment(
    organization_id: str,
    model_id: str,
    body: RiskAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        ra = await db.run_sync(
            lambda s: control_service.create_risk_assessment(
                model_id=model_id,
                actor_id=actor_id,
                session=s,
                use_case_id=body.use_case_id,
                methodology=body.methodology,
                bias_risk=body.bias_risk,
                explainability_risk=body.explainability_risk,
                privacy_risk=body.privacy_risk,
                regulatory_risk=body.regulatory_risk,
                operational_risk=body.operational_risk,
                overall_score=body.overall_score,
                rationale=body.rationale,
            )
        )
        await db.refresh(ra)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return ra


# ── Controls ──────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/controls",
    response_model=AIControlResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_control(
    organization_id: str,
    body: AIControlCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        ctrl = await db.run_sync(
            lambda s: control_service.create_control(
                organization_id=organization_id,
                name=body.name,
                control_type=body.control_type,
                actor_id=actor_id,
                session=s,
                description=body.description,
                examples=body.examples,
                model_id=body.model_id,
            )
        )
        await db.refresh(ctrl)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return ctrl


@router.get("/{organization_id}/controls", response_model=list[AIControlResponse])
async def list_controls(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: control_service.list_controls(organization_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/controls/{control_id}/tests",
    response_model=ControlTestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_control_test(
    organization_id: str,
    control_id: str,
    body: ControlTestCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        t = await db.run_sync(
            lambda s: control_service.record_control_test(
                control_id=control_id,
                test_result=body.test_result,
                actor_id=actor_id,
                session=s,
                model_id=body.model_id,
                notes=body.notes,
            )
        )
        await db.refresh(t)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return t


@router.get(
    "/{organization_id}/controls/{control_id}/tests",
    response_model=list[ControlTestResponse],
)
async def list_control_tests(
    organization_id: str,
    control_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: control_service.list_control_tests(control_id, s, limit=limit, offset=offset)
    )


# ── Prompt Templates ──────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/prompts",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    organization_id: str,
    body: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    pt = await db.run_sync(
        lambda s: prompt_service.create_prompt_template(
            organization_id=organization_id,
            name=body.name,
            prompt_text=body.prompt_text,
            actor_id=actor_id,
            session=s,
            model_id=body.model_id,
            owner_user_id=body.owner_user_id,
        )
    )
    await db.refresh(pt)
    return pt


@router.get("/{organization_id}/prompts", response_model=list[PromptTemplateResponse])
async def list_prompts(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: prompt_service.list_prompt_templates(
            organization_id, s, limit=limit, offset=offset
        )
    )


@router.get("/{organization_id}/prompts/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt(
    organization_id: str,
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    pt = await db.run_sync(lambda s: prompt_service.get_prompt_template(prompt_id, s))
    if not pt or pt.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return pt


@router.post(
    "/{organization_id}/prompts/{prompt_id}/approve",
    response_model=PromptTemplateResponse,
)
async def approve_prompt(
    organization_id: str,
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        pt = await db.run_sync(
            lambda s: prompt_service.approve_prompt_template(
                prompt_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(pt)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return pt


@router.post(
    "/{organization_id}/prompts/{prompt_id}/revise",
    response_model=PromptTemplateResponse,
)
async def revise_prompt(
    organization_id: str,
    prompt_id: str,
    body: PromptTemplateRevise,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        pt, _ = await db.run_sync(
            lambda s: prompt_service.revise_prompt_template(
                prompt_id=prompt_id,
                new_text=body.new_text,
                change_rationale=body.change_rationale,
                actor_id=actor_id,
                session=s,
                organization_id=organization_id,
            )
        )
        await db.refresh(pt)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return pt


@router.get(
    "/{organization_id}/prompts/{prompt_id}/history",
    response_model=list[PromptChangeResponse],
)
async def prompt_history(
    organization_id: str,
    prompt_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: prompt_service.list_prompt_changes(prompt_id, s, limit=limit, offset=offset)
    )


# ── Decision Logs ─────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/models/{model_id}/decisions",
    response_model=DecisionLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_decision(
    organization_id: str,
    model_id: str,
    body: DecisionLogCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    """Accepts pre-hashed SHA-256 values — raw data must never be sent here."""
    try:
        log = await db.run_sync(
            lambda s: decision_service.log_ai_decision(
                model_id=model_id,
                organization_id=organization_id,
                inputs_hash=body.inputs_hash,
                output_hash=body.output_hash,
                actor_id=actor_id,
                session=s,
                prompt_id=body.prompt_id,
                use_case_id=body.use_case_id,
                user_id=body.user_id,
                decision_type=body.decision_type,
                metadata=body.metadata,
            )
        )
        await db.refresh(log)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return log


@router.get(
    "/{organization_id}/models/{model_id}/decisions",
    response_model=list[DecisionLogResponse],
)
async def list_decisions(
    organization_id: str,
    model_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: decision_service.list_decision_logs(model_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/decisions/{log_id}/explain",
    response_model=ExplanationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_explanation(
    organization_id: str,
    log_id: str,
    body: ExplanationCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    exp = await db.run_sync(
        lambda s: decision_service.add_explanation(
            decision_log_id=log_id,
            actor_id=actor_id,
            session=s,
            factors=body.factors,
            confidence=body.confidence,
            rationale=body.rationale,
            source_references=body.source_references,
        )
    )
    await db.refresh(exp)
    return exp


@router.post(
    "/{organization_id}/models/{model_id}/reviews",
    response_model=HumanReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_human_review(
    organization_id: str,
    model_id: str,
    body: HumanReviewCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        review = await db.run_sync(
            lambda s: decision_service.submit_human_review(
                model_id=model_id,
                reviewer_user_id=actor_id,
                decision=body.decision,
                session=s,
                decision_log_id=body.decision_log_id,
                incident_id=body.incident_id,
                override_reason=body.override_reason,
                rationale=body.rationale,
            )
        )
        await db.refresh(review)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return review


# ── Monitoring ────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/models/{model_id}/monitoring",
    response_model=MonitoringSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_monitoring(
    organization_id: str,
    model_id: str,
    body: MonitoringSnapshotCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: monitoring_service.record_monitoring_snapshot(
            model_id=model_id,
            organization_id=organization_id,
            period_start=body.period_start,
            period_end=body.period_end,
            actor_id=actor_id,
            session=s,
            avg_latency_ms=body.avg_latency_ms,
            failure_count=body.failure_count,
            usage_count=body.usage_count,
            avg_confidence=body.avg_confidence,
            drift_score=body.drift_score,
            notes=body.notes,
        )
    )
    await db.refresh(rec)
    return rec


@router.get(
    "/{organization_id}/models/{model_id}/drift-alerts",
    response_model=list[DriftAlertResponse],
)
async def list_drift_alerts(
    organization_id: str,
    model_id: str,
    unresolved_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: monitoring_service.list_drift_alerts(
            model_id, s, unresolved_only=unresolved_only, limit=limit, offset=offset
        )
    )


@router.post(
    "/{organization_id}/drift-alerts/{alert_id}/resolve",
    response_model=DriftAlertResponse,
)
async def resolve_drift_alert(
    organization_id: str,
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        alert = await db.run_sync(
            lambda s: monitoring_service.resolve_drift_alert(
                alert_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(alert)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return alert


# ── Incidents ─────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/incidents",
    response_model=AIIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_incident(
    organization_id: str,
    body: AIIncidentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    if not body.model_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="model_id is required when using the flat /incidents endpoint",
        )
    try:
        inc = await db.run_sync(
            lambda s: incident_service.report_incident(
                model_id=body.model_id,
                organization_id=organization_id,
                incident_type=body.incident_type,
                severity=body.severity,
                description=body.description,
                actor_id=actor_id,
                session=s,
                reported_by=body.reported_by or actor_id,
            )
        )
        await db.refresh(inc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return inc


@router.post(
    "/{organization_id}/models/{model_id}/incidents",
    response_model=AIIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_model_incident(
    organization_id: str,
    model_id: str,
    body: AIIncidentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        inc = await db.run_sync(
            lambda s: incident_service.report_incident(
                model_id=model_id,
                organization_id=organization_id,
                incident_type=body.incident_type,
                severity=body.severity,
                description=body.description,
                actor_id=actor_id,
                session=s,
                reported_by=body.reported_by or actor_id,
            )
        )
        await db.refresh(inc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return inc


@router.get("/{organization_id}/incidents", response_model=list[AIIncidentResponse])
async def list_incidents(
    organization_id: str,
    unresolved_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: incident_service.list_incidents(
            organization_id, s,
            unresolved_only=unresolved_only,
            limit=limit,
            offset=offset,
        )
    )


@router.post(
    "/{organization_id}/incidents/{incident_id}/resolve",
    response_model=AIIncidentResponse,
)
async def resolve_incident(
    organization_id: str,
    incident_id: str,
    body: AIIncidentResolve,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        inc = await db.run_sync(
            lambda s: incident_service.resolve_incident(
                incident_id=incident_id,
                actor_id=actor_id,
                session=s,
                organization_id=organization_id,
                esg_action_id=body.esg_action_id,
                strategic_risk_id=body.strategic_risk_id,
            )
        )
        await db.refresh(inc)
    except AIGovernanceConflict as exc:
        raise _gov_conflict(exc)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return inc


# ── Policies ──────────────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/policies",
    response_model=AIPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(
    organization_id: str,
    body: AIPolicyCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        p = await db.run_sync(
            lambda s: monitoring_service.create_ai_policy(
                name=body.name,
                policy_type=body.policy_type,
                actor_id=actor_id,
                session=s,
                organization_id=organization_id,
                enterprise_id=body.enterprise_id,
                description=body.description,
                policy_body=body.policy_body,
            )
        )
        await db.refresh(p)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return p


@router.get("/{organization_id}/policies", response_model=list[AIPolicyResponse])
async def list_policies(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: monitoring_service.list_ai_policies(
            s, organization_id=organization_id, limit=limit, offset=offset
        )
    )


# ── Regulation Mappings ───────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/regulation-mappings",
    response_model=RegulationMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_regulation_mapping(
    organization_id: str,
    body: RegulationMappingCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rm = await db.run_sync(
            lambda s: control_service.create_regulation_mapping(
                framework=body.framework,
                organization_id=organization_id,
                actor_id=actor_id,
                session=s,
                use_case_id=body.use_case_id,
                risk_assessment_id=body.risk_assessment_id,
                control_id=body.control_id,
                article_reference=body.article_reference,
                requirement_text=body.requirement_text,
                compliance_status=body.compliance_status,
                notes=body.notes,
            )
        )
        await db.refresh(rm)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return rm


@router.get(
    "/{organization_id}/regulation-mappings",
    response_model=list[RegulationMappingResponse],
)
async def list_regulation_mappings(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: control_service.list_regulation_mappings(
            organization_id, s, limit=limit, offset=offset
        )
    )


@router.patch(
    "/{organization_id}/regulation-mappings/{mapping_id}/status",
    response_model=RegulationMappingResponse,
)
async def update_regulation_mapping_status(
    organization_id: str,
    mapping_id: str,
    body: RegulationMappingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rm = await db.run_sync(
            lambda s: control_service.update_regulation_mapping_status(
                mapping_id=mapping_id,
                new_status=body.compliance_status,
                actor_id=actor_id,
                session=s,
                organization_id=organization_id,
            )
        )
        await db.refresh(rm)
    except AIGovernanceError as exc:
        raise _gov_error(exc)
    return rm


# ── Assurance Reports ─────────────────────────────────────────────────────────

@router.post(
    "/{organization_id}/assurance-reports",
    response_model=AssuranceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_assurance_report(
    organization_id: str,
    body: AssuranceReportCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    report = await db.run_sync(
        lambda s: assurance_service.generate_assurance_report(
            organization_id=organization_id,
            title=body.title,
            period_start=body.period_start,
            period_end=body.period_end,
            actor_id=actor_id,
            session=s,
        )
    )
    await db.refresh(report)
    return report


@router.get(
    "/{organization_id}/assurance-reports",
    response_model=list[AssuranceReportResponse],
)
async def list_assurance_reports(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: assurance_service.list_assurance_reports(
            organization_id, s, limit=limit, offset=offset
        )
    )


@router.get(
    "/{organization_id}/assurance-reports/{report_id}",
    response_model=AssuranceReportResponse,
)
async def get_assurance_report(
    organization_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    r = await db.run_sync(
        lambda s: assurance_service.get_assurance_report(report_id, s)
    )
    if not r or r.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return r
