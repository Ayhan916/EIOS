from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from application.agents.base import AgentContext
from application.agents.registry import AGENT_TYPES, get_agent
from domain.agent_run import AgentRun
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.llm.deps import get_llm_provider
from infrastructure.persistence.repositories.agent_run import SQLAgentRunRepository
from interfaces.api.deps import get_agent_run_repo, get_current_user
from interfaces.api.schemas.agent import AgentRunRequest, AgentRunResponse
from shared.rate_limit import rate_limit_llm

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
)


def _run_to_response(run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        agent_type=run.agent_type,
        query=run.query,
        result_content=run.result_content,
        confidence=run.confidence,
        reasoning=run.reasoning,
        llm_provider=run.llm_provider,
        llm_model=run.llm_model,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        error=run.error,
        run_metadata=run.run_metadata,
        status=run.status.value,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/run", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def run_agent(
    body: AgentRunRequest,
    _rl: None = Depends(rate_limit_llm),
    current_user: User = Depends(get_current_user),
    repo: SQLAgentRunRepository = Depends(get_agent_run_repo),
) -> AgentRunResponse:
    """Run a single EIOS agent and persist the result."""
    if body.agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown agent_type '{body.agent_type}'. Valid types: {AGENT_TYPES}",
        )

    provider = get_llm_provider()
    agent = get_agent(body.agent_type, provider)

    context = AgentContext(
        query=body.query,
        knowledge_chunks=body.knowledge_chunks,
        prior_outputs=body.prior_outputs,
        metadata=body.metadata,
    )

    run = AgentRun(
        agent_type=body.agent_type,
        query=body.query,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
        run_metadata=body.metadata,
    )

    try:
        result = await agent.run(context)

        run.result_content = result.content
        run.confidence = result.confidence
        run.reasoning = result.reasoning

        if result.llm_response is not None:
            run.llm_provider = result.llm_response.provider
            run.llm_model = result.llm_response.model
            run.input_tokens = result.llm_response.input_tokens
            run.output_tokens = result.llm_response.output_tokens

        logger.info(
            "agent_run_complete",
            agent_type=body.agent_type,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
        )

    except Exception as exc:
        run.error = str(exc)
        run.status = EntityStatus.SUSPENDED
        logger.error("agent_run_failed", agent_type=body.agent_type, error=str(exc))

    saved = await repo.save(run)
    return _run_to_response(saved)


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_agent_runs(
    repo: SQLAgentRunRepository = Depends(get_agent_run_repo),
) -> list[AgentRunResponse]:
    """List all agent runs."""
    runs = await repo.list_all()
    return [_run_to_response(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: str,
    repo: SQLAgentRunRepository = Depends(get_agent_run_repo),
) -> AgentRunResponse:
    """Get a single agent run by ID."""
    run = await repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AgentRun {run_id} not found",
        )
    return _run_to_response(run)
