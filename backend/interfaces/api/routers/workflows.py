from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from application.workflows.executor import execute_workflow_background
from application.workflows.registry import WORKFLOW_TYPES, get_workflow_definition
from domain.user import User
from domain.workflow_job import WorkflowJob
from domain.workflow_run import WorkflowRun
from infrastructure.persistence.repositories.agent_run import SQLAgentRunRepository
from infrastructure.persistence.repositories.workflow_job import SQLWorkflowJobRepository
from infrastructure.persistence.repositories.workflow_run import SQLWorkflowRunRepository
from interfaces.api.deps import (
    get_agent_run_repo,
    get_current_user,
    get_workflow_job_repo,
    get_workflow_run_repo,
    require_analyst,
)
from interfaces.api.schemas.pagination import Page, PaginationParams
from interfaces.api.schemas.workflow import (
    AgentStepSummary,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowTypeInfo,
)
from interfaces.api.schemas.workflow_job import WorkflowJobResponse

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)


def _build_run_response(run: WorkflowRun, steps: list[AgentStepSummary]) -> WorkflowRunResponse:
    return WorkflowRunResponse(
        id=run.id,
        workflow_type=run.workflow_type,
        query=run.query,
        verdict=run.verdict,
        verdict_reasoning=run.verdict_reasoning,
        overall_risk_level=run.overall_risk_level,
        steps_completed=run.steps_completed,
        total_steps=run.total_steps,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        error=run.error,
        assessment_id=run.assessment_id,
        finding_count=run.finding_count,
        risk_count=run.risk_count,
        recommendation_count=run.recommendation_count,
        run_metadata=run.run_metadata,
        status=run.status.value,
        created_at=run.created_at,
        updated_at=run.updated_at,
        steps=steps,
    )


def _build_job_response(job: WorkflowJob) -> WorkflowJobResponse:
    return WorkflowJobResponse(
        id=job.id,
        workflow_type=job.workflow_type,
        query=job.query,
        job_status=job.job_status,
        workflow_run_id=job.workflow_run_id,
        error=job.error,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/types", response_model=list[WorkflowTypeInfo])
async def list_workflow_types() -> list[WorkflowTypeInfo]:
    """Return all available workflow types with their agent sequences."""
    from application.workflows.registry import _REGISTRY
    result = []
    for wt in WORKFLOW_TYPES:
        defn = _REGISTRY[wt]
        result.append(WorkflowTypeInfo(
            workflow_type=wt,
            description=defn.description,
            step_count=len(defn.steps),
            agent_sequence=[s.agent_type for s in defn.steps],
        ))
    return result


@router.post(
    "/run",
    response_model=WorkflowJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_analyst)],
)
async def run_workflow(
    body: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    job_repo: SQLWorkflowJobRepository = Depends(get_workflow_job_repo),
) -> WorkflowJobResponse:
    """
    Submit a workflow for async execution.

    Returns 202 immediately with a job_id. Poll GET /workflows/jobs/{id}
    for status. When completed, workflow_run_id is populated.
    """
    if body.workflow_type not in WORKFLOW_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown workflow_type '{body.workflow_type}'. Valid types: {WORKFLOW_TYPES}",
        )

    # Validate workflow type exists in registry (fail fast before enqueuing)
    get_workflow_definition(body.workflow_type)

    job = WorkflowJob(
        workflow_type=body.workflow_type,
        query=body.query,
        created_by=current_user.id,
        organization_id=current_user.organization_id,
        job_metadata=body.metadata or {},
    )
    saved_job = await job_repo.save(job)

    background_tasks.add_task(
        execute_workflow_background,
        job=saved_job,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )

    logger.info(
        "workflow_job_enqueued",
        job_id=saved_job.id,
        workflow_type=body.workflow_type,
        user_id=current_user.id,
    )

    return _build_job_response(saved_job)


@router.get("/jobs", response_model=Page[WorkflowJobResponse])
async def list_workflow_jobs(
    pagination: PaginationParams = Depends(),
    job_status: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    job_repo: SQLWorkflowJobRepository = Depends(get_workflow_job_repo),
) -> Page[WorkflowJobResponse]:
    """List workflow jobs for the current user's organization, newest first."""
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await job_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        job_status=job_status,
    )
    return Page(
        items=[_build_job_response(j) for j in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/jobs/{job_id}", response_model=WorkflowJobResponse)
async def get_workflow_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    job_repo: SQLWorkflowJobRepository = Depends(get_workflow_job_repo),
) -> WorkflowJobResponse:
    """Get the status of a workflow job. workflow_run_id is set when completed."""
    job = await job_repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowJob {job_id} not found",
        )
    if job.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return _build_job_response(job)


@router.get("/runs", response_model=Page[WorkflowRunResponse])
async def list_workflow_runs(
    pagination: PaginationParams = Depends(),
    workflow_type: Optional[str] = Query(default=None),
    verdict: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    workflow_run_repo: SQLWorkflowRunRepository = Depends(get_workflow_run_repo),
) -> Page[WorkflowRunResponse]:
    """List workflow runs for the current user's organization, newest first."""
    if not current_user.organization_id:
        return Page(items=[], total=0, page=pagination.page, page_size=pagination.page_size)
    items, total = await workflow_run_repo.list_org_paged(
        organization_id=current_user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        workflow_type=workflow_type,
        verdict=verdict,
    )
    return Page(
        items=[_build_run_response(run, steps=[]) for run in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    workflow_run_repo: SQLWorkflowRunRepository = Depends(get_workflow_run_repo),
    agent_run_repo: SQLAgentRunRepository = Depends(get_agent_run_repo),
) -> WorkflowRunResponse:
    """Get a completed workflow run with all agent steps."""
    run = await workflow_run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun {run_id} not found",
        )
    # Tenant isolation: cross-org access returns 404
    if (
        run.organization_id
        and current_user.organization_id
        and run.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun {run_id} not found",
        )
    agent_runs = await agent_run_repo.list_by_workflow_run(run_id)
    steps = [
        AgentStepSummary(
            agent_run_id=ar.id,
            agent_type=ar.agent_type,
            step_index=ar.step_index,
            status=ar.status.value,
            input_tokens=ar.input_tokens,
            output_tokens=ar.output_tokens,
            error=ar.error,
        )
        for ar in sorted(agent_runs, key=lambda a: a.step_index)
    ]
    return _build_run_response(run, steps)


@router.get("/runs/{run_id}/steps/{step_index}/output", response_model=dict)
async def get_step_output(
    run_id: str,
    step_index: int,
    current_user: User = Depends(get_current_user),
    workflow_run_repo: SQLWorkflowRunRepository = Depends(get_workflow_run_repo),
    agent_run_repo: SQLAgentRunRepository = Depends(get_agent_run_repo),
) -> dict:
    """Retrieve the full LLM output for a specific workflow step."""
    # Tenant isolation: verify the parent run belongs to the user's org
    run = await workflow_run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun {run_id} not found",
        )
    if (
        run.organization_id
        and current_user.organization_id
        and run.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowRun {run_id} not found",
        )
    agent_runs = await agent_run_repo.list_by_workflow_run(run_id)
    step = next((ar for ar in agent_runs if ar.step_index == step_index), None)
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_index} not found in WorkflowRun {run_id}",
        )
    return {
        "agent_run_id": step.id,
        "agent_type": step.agent_type,
        "step_index": step.step_index,
        "content": step.result_content,
        "confidence": step.confidence,
        "reasoning": step.reasoning,
        "input_tokens": step.input_tokens,
        "output_tokens": step.output_tokens,
        "llm_provider": step.llm_provider,
        "llm_model": step.llm_model,
        "error": step.error,
    }
