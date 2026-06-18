"""
Async workflow background executor.

This module intentionally bridges Application and Infrastructure layers:
background task coordinators must create their own DB sessions and cannot
use request-scoped DI. This is a documented architectural concession for M12.

Session strategy (avoids long-lived transactions during 60-180s LLM execution):
  Phase 1: mark job "running"
  Phase 2: run engine (LLM calls) with a separate read-only knowledge session
  Phase 3: persist all results + mark job "completed"
  On error: mark job "failed"
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import update

import application.audit as audit_factory  # noqa: E402
from application.extraction.service import StructuredExtractionService
from application.workflows.engine import WorkflowEngine
from application.workflows.registry import get_workflow_definition
from domain.workflow_job import WorkflowJob
from infrastructure.embeddings.deps import get_embedding_provider
from infrastructure.knowledge_search import EvidenceChunkSearchAdapter
from infrastructure.llm.deps import get_llm_provider
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.workflow_job import WorkflowJobModel
import application.notification_service as notification_service
from domain.enums import NotificationType
from infrastructure.persistence.repositories.agent_run import SQLAgentRunRepository
from infrastructure.persistence.repositories.assessment import SQLAssessmentRepository
from infrastructure.persistence.repositories.audit_event import SQLAuditEventRepository
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository
from application.extraction.evidence_linker import (
    create_finding_evidence_links,
    update_finding_evidence_strength,
)
from infrastructure.persistence.repositories.finding import SQLFindingRepository
from infrastructure.persistence.repositories.finding_evidence_link import SQLFindingEvidenceLinkRepository
from infrastructure.persistence.repositories.recommendation import SQLRecommendationRepository
from infrastructure.persistence.repositories.risk import SQLRiskRepository
from infrastructure.persistence.repositories.user import SQLUserRepository
from infrastructure.persistence.repositories.workflow_job import SQLWorkflowJobRepository
from infrastructure.persistence.repositories.workflow_run import SQLWorkflowRunRepository

logger = structlog.get_logger(__name__)

_extractor = StructuredExtractionService()


async def execute_workflow_background(
    job: WorkflowJob,
    user_id: str,
    organization_id: str | None = None,
) -> None:
    """
    Execute a workflow as a background task.

    Manages its own DB sessions so the HTTP request session can close
    immediately after returning 202.
    """
    log = logger.bind(job_id=job.id, workflow_type=job.workflow_type, user_id=user_id)
    log.info("workflow_job_started")

    # Phase 1: mark running via UPDATE only.
    # BaseHTTPMiddleware starts background tasks before the route handler's DI
    # session commits, so session.merge() would see no row and issue a conflicting
    # INSERT. A pure UPDATE is safe: if the row isn't committed yet it affects 0
    # rows silently; the job stays "pending" until Phase 3 marks it "completed".
    async with AsyncSessionFactory() as session, session.begin():
        await session.execute(
            update(WorkflowJobModel)
            .where(WorkflowJobModel.id == job.id)
            .values(job_status="running", started_at=datetime.now(UTC))
        )

    # Phase 2: execute workflow (LLM calls — no DB transaction held open)
    try:
        definition = get_workflow_definition(job.workflow_type)
        llm_provider = get_llm_provider()
        embedding_provider = get_embedding_provider()

        async with AsyncSessionFactory() as ks_session:
            chunk_repo = SQLEvidenceChunkRepository(ks_session)
            knowledge_search = EvidenceChunkSearchAdapter(chunk_repo, embedding_provider)
            engine = WorkflowEngine(llm_provider=llm_provider, knowledge_search=knowledge_search)

            workflow_run, agent_runs = await engine.run(
                definition=definition,
                query=job.query,
                metadata=job.job_metadata,
                created_by=user_id,
                organization_id=organization_id,
            )
            workflow_run.organization_id = organization_id

    except Exception as exc:
        log.error("workflow_job_engine_failed", error=str(exc))
        async with AsyncSessionFactory() as session, session.begin():
            job_repo = SQLWorkflowJobRepository(session)
            job.job_status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(UTC)
            await job_repo.save(job)
        return

    # Record aggregate token usage to in-process metrics counter
    try:
        from interfaces.api.routers.metrics import counters
        total_tokens = workflow_run.total_input_tokens + workflow_run.total_output_tokens
        counters.record_llm_call(total_tokens)
    except Exception:
        pass

    # Phase 3: persist all results
    try:
        async with AsyncSessionFactory() as session, session.begin():
            wf_run_repo = SQLWorkflowRunRepository(session)
            agent_run_repo = SQLAgentRunRepository(session)
            audit_repo = SQLAuditEventRepository(session)
            job_repo = SQLWorkflowJobRepository(session)

            saved_run = await wf_run_repo.save(workflow_run)

            for ar in agent_runs:
                await agent_run_repo.save(ar)

            step_outputs: dict[str, str] = {
                ar.agent_type: (ar.result_content or "")
                for ar in agent_runs
                if not ar.error and ar.result_content
            }

            assessment_id: str | None = None
            finding_count = 0
            risk_count = 0
            recommendation_count = 0

            if step_outputs:
                try:
                    assessment, findings, risks, recommendations = _extractor.extract(
                        workflow_run=saved_run,
                        step_outputs=step_outputs,
                        created_by=user_id,
                        organization_id=organization_id,
                    )

                    assess_repo = SQLAssessmentRepository(session)
                    finding_repo = SQLFindingRepository(session)
                    risk_repo = SQLRiskRepository(session)
                    rec_repo = SQLRecommendationRepository(session)
                    link_repo = SQLFindingEvidenceLinkRepository(session)

                    saved_assessment = await assess_repo.save(assessment)
                    assessment_id = saved_assessment.id

                    for f in findings:
                        await finding_repo.save(f)
                    for r in risks:
                        await risk_repo.save(r)
                    for rec in recommendations:
                        await rec_repo.save(rec)

                    # M25: create traceable evidence links
                    retrieved_chunks = saved_run.run_metadata.get("retrieved_chunks", [])
                    if retrieved_chunks and findings:
                        try:
                            links = create_finding_evidence_links(
                                findings=findings,
                                retrieved_chunks=retrieved_chunks,
                                created_by=user_id,
                            )
                            for link in links:
                                await link_repo.save(link)

                            # Group by finding and update strength + source count
                            from collections import defaultdict
                            links_by_finding: dict[str, list] = defaultdict(list)
                            for lnk in links:
                                links_by_finding[lnk.finding_id].append(lnk)
                            for f in findings:
                                update_finding_evidence_strength(f, links_by_finding[f.id])
                                await finding_repo.save(f)

                            log.info(
                                "evidence_links_created",
                                link_count=len(links),
                                finding_count=len(findings),
                            )
                        except Exception as link_exc:
                            log.warning("evidence_linking_failed", error=str(link_exc))

                    finding_count = len(findings)
                    risk_count = len(risks)
                    recommendation_count = len(recommendations)

                    saved_run.assessment_id = assessment_id
                    saved_run.finding_count = finding_count
                    saved_run.risk_count = risk_count
                    saved_run.recommendation_count = recommendation_count
                    saved_run = await wf_run_repo.save(saved_run)

                    await audit_repo.save(
                        audit_factory.assessment_created(
                            assessment_id=assessment_id,
                            workflow_run_id=saved_run.id,
                            finding_count=finding_count,
                            risk_count=risk_count,
                            recommendation_count=recommendation_count,
                            actor_id=user_id,
                        )
                    )

                    log.info(
                        "workflow_extraction_complete",
                        assessment_id=assessment_id,
                        findings=finding_count,
                        risks=risk_count,
                        recommendations=recommendation_count,
                    )

                except Exception as exc:
                    log.warning("workflow_extraction_failed", error=str(exc))

            await audit_repo.save(
                audit_factory.workflow_completed(
                    workflow_run_id=saved_run.id,
                    workflow_type=job.workflow_type,
                    verdict=saved_run.verdict,
                    actor_id=user_id,
                    assessment_id=assessment_id,
                )
            )

            job.job_status = "completed"
            job.workflow_run_id = saved_run.id
            job.completed_at = datetime.now(UTC)
            await job_repo.save(job)

            # In-app notification: workflow completed
            try:
                user_repo = SQLUserRepository(session)
                user = await user_repo.get_by_id(user_id)
                if user:
                    verdict_str = f" Verdict: {saved_run.verdict}." if saved_run.verdict else ""
                    await notification_service.notify(
                        session=session,
                        user_id=user_id,
                        organization_id=organization_id or "",
                        notification_type=NotificationType.WORKFLOW_COMPLETED,
                        title="Workflow analysis complete",
                        body=f"Your {job.workflow_type} workflow has finished.{verdict_str}",
                        entity_type="workflow_run",
                        entity_id=saved_run.id,
                        dedupe_key=f"workflow_completed:{saved_run.id}",
                        user_email=user.email,
                    )
            except Exception as notif_exc:
                log.warning("workflow_notification_failed", error=str(notif_exc))

        log.info("workflow_job_completed", workflow_run_id=saved_run.id)

    except Exception as exc:
        log.error("workflow_job_persist_failed", error=str(exc))
        async with AsyncSessionFactory() as session, session.begin():
            job_repo = SQLWorkflowJobRepository(session)
            job.job_status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(UTC)
            await job_repo.save(job)
