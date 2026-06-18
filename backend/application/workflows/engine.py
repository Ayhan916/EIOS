from __future__ import annotations

import structlog

from application.agents.base import AgentContext
from application.agents.registry import get_agent
from application.budget.tracker import BudgetExceededError, budget_tracker
from application.ports.knowledge import KnowledgeSearchPort
from application.ports.llm import LLMProvider
from application.workflows.base import StepResult, WorkflowDefinition, extract_verdict
from domain.agent_run import AgentRun
from domain.enums import EntityStatus
from domain.workflow_run import WorkflowRun

logger = structlog.get_logger(__name__)


class WorkflowEngine:
    """Executes a WorkflowDefinition step-by-step.

    Depends only on abstract ports (LLMProvider, KnowledgeSearchPort).
    Repositories are injected — infrastructure details stay out of this layer.
    Persistence of AgentRun and WorkflowRun records is handled externally by
    the caller (the API router) after run() returns, so the engine remains
    free of database coupling.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge_search: KnowledgeSearchPort | None = None,
    ) -> None:
        self._llm = llm_provider
        self._knowledge = knowledge_search

    async def run(
        self,
        definition: WorkflowDefinition,
        query: str,
        metadata: dict,
        created_by: str | None = None,
        organization_id: str | None = None,
    ) -> tuple[WorkflowRun, list[AgentRun]]:
        """Execute the workflow and return (WorkflowRun, [AgentRun, ...]).

        The caller is responsible for persisting both the WorkflowRun and all
        AgentRuns. This keeps the engine decoupled from the database session.
        """
        workflow_run = WorkflowRun(
            workflow_type=definition.workflow_type,
            query=query,
            total_steps=len(definition.steps),
            status=EntityStatus.ACTIVE,
            created_by=created_by,
            run_metadata=metadata,
        )

        agent_runs: list[AgentRun] = []
        step_results: list[StepResult] = []
        knowledge_chunks: list[str] = []
        all_retrieved_chunks: list[dict] = []

        for idx, step in enumerate(definition.steps):
            # Retrieve knowledge chunks if this step requests it
            if step.retrieve_knowledge and self._knowledge is not None:
                try:
                    rich_chunks = await self._knowledge.search(
                        query, limit=step.knowledge_limit
                    )
                    knowledge_chunks = [c.text for c in rich_chunks]
                    # Accumulate full metadata for evidence linking after extraction
                    all_retrieved_chunks.extend([c.to_dict() for c in rich_chunks])
                    logger.info(
                        "workflow_knowledge_retrieved",
                        workflow_type=definition.workflow_type,
                        step=step.agent_type,
                        chunks=len(knowledge_chunks),
                    )
                except Exception as exc:
                    logger.warning(
                        "workflow_knowledge_retrieval_failed",
                        step=step.agent_type,
                        error=str(exc),
                    )
                    knowledge_chunks = []

            prior_outputs = (
                [r.content for r in step_results if not r.error] if step.pass_prior_outputs else []
            )

            context = AgentContext(
                query=query,
                knowledge_chunks=knowledge_chunks,
                prior_outputs=prior_outputs,
                metadata=metadata,
            )

            agent = get_agent(step.agent_type, self._llm)

            agent_run = AgentRun(
                agent_type=step.agent_type,
                query=query,
                workflow_run_id=workflow_run.id,
                step_index=idx,
                status=EntityStatus.ACTIVE,
                created_by=created_by,
                run_metadata=metadata,
            )

            step_result = StepResult(
                agent_type=step.agent_type,
                step_index=idx,
                content="",
            )

            try:
                result = await agent.run(context)
                agent_run.result_content = result.content
                agent_run.confidence = result.confidence
                agent_run.reasoning = result.reasoning

                if result.llm_response is not None:
                    agent_run.llm_provider = result.llm_response.provider
                    agent_run.llm_model = result.llm_response.model
                    agent_run.input_tokens = result.llm_response.input_tokens
                    agent_run.output_tokens = result.llm_response.output_tokens

                step_result.content = result.content
                step_result.input_tokens = agent_run.input_tokens
                step_result.output_tokens = agent_run.output_tokens
                step_result.llm_provider = agent_run.llm_provider
                step_result.llm_model = agent_run.llm_model

                # Record token usage against org budget (no-op when budget=0)
                step_tokens = agent_run.input_tokens + agent_run.output_tokens
                if organization_id and step_tokens > 0:
                    try:
                        budget_tracker.check_and_record(organization_id, step_tokens)
                    except BudgetExceededError as budget_err:
                        raise budget_err

                logger.info(
                    "workflow_step_complete",
                    workflow_type=definition.workflow_type,
                    step=step.agent_type,
                    step_index=idx,
                    output_tokens=agent_run.output_tokens,
                )

            except BudgetExceededError:
                raise

            except Exception as exc:
                error_msg = str(exc)
                agent_run.error = error_msg
                agent_run.status = EntityStatus.SUSPENDED
                step_result.error = error_msg
                logger.error(
                    "workflow_step_failed",
                    workflow_type=definition.workflow_type,
                    step=step.agent_type,
                    error=error_msg,
                )

            agent_runs.append(agent_run)
            step_results.append(step_result)
            workflow_run.steps_completed = idx + 1

        # Store retrieved chunk metadata for evidence linking (consumed by executor → evidence_linker)
        if all_retrieved_chunks:
            workflow_run.run_metadata = {**workflow_run.run_metadata, "retrieved_chunks": all_retrieved_chunks}

        # Aggregate token usage
        workflow_run.total_input_tokens = sum(r.input_tokens for r in step_results)
        workflow_run.total_output_tokens = sum(r.output_tokens for r in step_results)

        # Extract structured verdict
        verdict, risk_level = extract_verdict(step_results)
        workflow_run.verdict = verdict
        workflow_run.overall_risk_level = risk_level

        # Build verdict reasoning from reporting agent if available
        reporting = next(
            (r for r in step_results if r.agent_type == "reporting" and not r.error), None
        )
        if reporting:
            lines = reporting.content.strip().split("\n")
            workflow_run.verdict_reasoning = "\n".join(lines[:5])
        elif step_results:
            last_success = next((r for r in reversed(step_results) if not r.error), None)
            if last_success:
                lines = last_success.content.strip().split("\n")
                workflow_run.verdict_reasoning = "\n".join(lines[:3])

        failed_steps = sum(1 for r in step_results if r.error)
        if failed_steps == len(step_results):
            workflow_run.status = EntityStatus.SUSPENDED
            workflow_run.error = "All workflow steps failed"
        elif failed_steps > 0:
            workflow_run.status = EntityStatus.REVIEWED
        else:
            workflow_run.status = EntityStatus.APPROVED

        logger.info(
            "workflow_complete",
            workflow_type=definition.workflow_type,
            verdict=verdict,
            risk_level=risk_level,
            steps=len(step_results),
            failed=failed_steps,
        )

        return workflow_run, agent_runs
