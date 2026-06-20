"""
EIOS Backend — FastAPI Application Entry Point

Clean Architecture: Interfaces layer wires up the HTTP transport.
Domain and Application layers have no knowledge of FastAPI.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import (
    MetricsCounterMiddleware,
    RequestBodySizeLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from infrastructure.embeddings.deps import init_embedding_provider
from infrastructure.llm.deps import init_llm_provider
from interfaces.api.routers import (
    agents_router,
    api_platform_router,
    copilot_router,
    disclosure_router,
    due_diligence_router,
    external_intelligence_router,
    operations_router,
    regulatory_router,
    assessments_benchmark_router,
    assessments_compliance_router,
    assessments_router,
    audit_router,
    auth_router,
    comments_router,
    dashboard_router,
    evidences_router,
    executive_router,
    findings_router,
    frameworks_router,
    health_router,
    knowledge_router,
    metrics_router,
    notifications_router,
    organizations_router,
    recommendations_router,
    reports_router,
    risks_router,
    sector_intelligence_router,
    sectors_router,
    supplier_intelligence_router,
    supplier_portal_router,
    supplier_portal_internal_router,
    suppliers_router,
    users_router,
    workflows_router,
    agent_monitoring_router,
    surveillance_router,
)
from shared.config import settings

# ── Background tasks ──────────────────────────────────────────────────────────

_overdue_task: asyncio.Task | None = None
_webhook_recovery_task: asyncio.Task | None = None
_intelligence_scheduler_task: asyncio.Task | None = None
_agent_scheduler_task: asyncio.Task | None = None


async def _check_overdue_loop() -> None:
    """
    Runs every 6 hours. Fires ACTION_OVERDUE notifications for past-due recommendations.

    Query strategy: single JOIN per batch (recs + user in one round-trip).
    Processes in batches of 500 to avoid loading the full table into memory.
    Passes pre-fetched notification_preferences to notify() to eliminate the
    second per-row user lookup inside the service.
    Total DB cost: ceil(overdue_count / 500) queries + 1 dedupe-check + 1 INSERT per new notif.
    """
    from infrastructure.persistence.database import AsyncSessionFactory
    from infrastructure.persistence.repositories.recommendation import SQLRecommendationRepository
    from application import notification_service
    from domain.enums import NotificationType

    _BATCH = 500
    log = structlog.get_logger("overdue_task")
    while True:
        await asyncio.sleep(6 * 3600)
        today = date.today()
        offset = 0
        total_sent = 0
        try:
            while True:
                async with AsyncSessionFactory() as session, session.begin():
                    rec_repo = SQLRecommendationRepository(session)
                    batch = await rec_repo.list_overdue_with_assignees(
                        today, limit=_BATCH, offset=offset
                    )
                    for row in batch:
                        try:
                            await notification_service.notify(
                                session=session,
                                user_id=row.user_id,
                                organization_id=row.organization_id,
                                notification_type=NotificationType.ACTION_OVERDUE,
                                title="Action overdue",
                                body=f"Recommendation '{row.recommendation_title}' was due on {row.due_date}.",
                                entity_type="recommendation",
                                entity_id=row.recommendation_id,
                                dedupe_key=f"overdue:{row.recommendation_id}:{today}",
                                user_email=row.user_email,
                                notification_preferences=row.notification_preferences,
                            )
                            total_sent += 1
                        except Exception as row_exc:
                            log.warning(
                                "overdue_notify_failed",
                                recommendation_id=row.recommendation_id,
                                error=str(row_exc),
                            )

                if len(batch) < _BATCH:
                    break
                offset += _BATCH

            log.info("overdue_scan_complete", notifications_sent=total_sent, date=str(today))
        except Exception as exc:
            log.error("overdue_check_failed", error=str(exc))


# ── Structured logging ─────────────────────────────────────────────────────────

_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
        if not settings.is_development
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

API_V1 = "/api/v1"


# ── Application lifespan ───────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Fail fast on production misconfiguration before accepting any traffic
    settings.validate_production()

    logger.info("eios_startup", environment=settings.environment, version="0.20.0")
    init_embedding_provider()
    logger.info("embedding_provider_ready", model=settings.embedding_model)

    if settings.anthropic_api_key or settings.openai_api_key or settings.groq_api_key:
        init_llm_provider()
        logger.info(
            "llm_provider_ready",
            provider=settings.llm_provider,
            model=settings.llm_model,
        )
    else:
        logger.warning(
            "llm_provider_not_configured",
            detail="Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable agent runs",
        )

    if settings.llm_monthly_token_budget > 0:
        logger.info(
            "llm_budget_active",
            monthly_token_budget=settings.llm_monthly_token_budget,
        )

    from application.api_platform.recovery_worker import run_webhook_recovery_loop  # noqa: PLC0415
    from application.compliance.seed_regulations import seed_regulatory_data  # noqa: PLC0415
    from application.disclosure.seed_frameworks import seed_disclosure_frameworks  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415

    # Seed regulatory frameworks (idempotent — only inserts if absent)
    try:
        async with AsyncSessionFactory() as _seed_session, _seed_session.begin():
            await seed_regulatory_data(_seed_session)
        logger.info("regulatory_seed_done")
    except Exception as _seed_exc:
        logger.warning("regulatory_seed_failed", error=str(_seed_exc))

    # Seed disclosure frameworks (idempotent — only inserts if absent)
    try:
        async with AsyncSessionFactory() as _dseed_session, _dseed_session.begin():
            await seed_disclosure_frameworks(_dseed_session)
        logger.info("disclosure_seed_done")
    except Exception as _dseed_exc:
        logger.warning("disclosure_seed_failed", error=str(_dseed_exc))

    # Seed M35 questionnaire templates (idempotent)
    from application.supplier_portal.questionnaire_service import seed_builtin_templates  # noqa: PLC0415
    try:
        async with AsyncSessionFactory() as _qseed_session, _qseed_session.begin():
            await seed_builtin_templates(_qseed_session)
        logger.info("questionnaire_templates_seed_done")
    except Exception as _qseed_exc:
        logger.warning("questionnaire_templates_seed_failed", error=str(_qseed_exc))

    # Seed M36 monitoring agents (idempotent)
    from application.agent_monitoring.agent_service import seed_monitoring_agents  # noqa: PLC0415
    try:
        async with AsyncSessionFactory() as _aseed_session, _aseed_session.begin():
            await seed_monitoring_agents(_aseed_session)
        logger.info("monitoring_agents_seed_done")
    except Exception as _aseed_exc:
        logger.warning("monitoring_agents_seed_failed", error=str(_aseed_exc))

    from application.external_intelligence.scheduler import run_intelligence_scheduler  # noqa: PLC0415
    from application.agent_monitoring.scheduler import run_agent_scheduler  # noqa: PLC0415

    global _overdue_task, _webhook_recovery_task, _intelligence_scheduler_task, _agent_scheduler_task
    _overdue_task = asyncio.create_task(_check_overdue_loop())
    logger.info("overdue_task_started")
    _webhook_recovery_task = asyncio.create_task(run_webhook_recovery_loop())
    logger.info("webhook_recovery_task_started")
    _intelligence_scheduler_task = asyncio.create_task(run_intelligence_scheduler())
    logger.info("intelligence_scheduler_started")
    _agent_scheduler_task = asyncio.create_task(run_agent_scheduler())
    logger.info("agent_scheduler_started")

    yield

    if _overdue_task is not None:
        _overdue_task.cancel()
    if _webhook_recovery_task is not None:
        _webhook_recovery_task.cancel()
    if _intelligence_scheduler_task is not None:
        _intelligence_scheduler_task.cancel()
    if _agent_scheduler_task is not None:
        _agent_scheduler_task.cancel()
    logger.info("eios_shutdown")


# ── FastAPI application ────────────────────────────────────────────────────────

app = FastAPI(
    title="EIOS — Enterprise Intelligence Operating System",
    description="ESG Due Diligence and Risk Intelligence Platform API",
    version="0.20.0",
    lifespan=lifespan,
    # Hide docs in production — expose via VPN or behind auth proxy if needed
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware stack (applied in reverse registration order) ───────────────────
# Execution order: RequestID → RequestLogging → SecurityHeaders → MetricsCounter → CORS → route

app.add_middleware(MetricsCounterMiddleware)
app.add_middleware(RequestBodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ───────────────────────────────────────────────────


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        path=str(request.url),
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router, prefix=API_V1)
app.include_router(organizations_router, prefix=API_V1)
app.include_router(sectors_router, prefix=API_V1)
app.include_router(assessments_router, prefix=API_V1)
app.include_router(findings_router, prefix=API_V1)
app.include_router(risks_router, prefix=API_V1)
app.include_router(evidences_router, prefix=API_V1)
app.include_router(recommendations_router, prefix=API_V1)
app.include_router(knowledge_router, prefix=API_V1)
app.include_router(agents_router, prefix=API_V1)
app.include_router(workflows_router, prefix=API_V1)
app.include_router(audit_router, prefix=API_V1)
app.include_router(frameworks_router, prefix=API_V1)
app.include_router(assessments_compliance_router, prefix=API_V1)
app.include_router(assessments_benchmark_router, prefix=API_V1)
app.include_router(reports_router, prefix=API_V1)
app.include_router(sector_intelligence_router, prefix=API_V1)
app.include_router(dashboard_router, prefix=API_V1)
app.include_router(users_router, prefix=API_V1)
app.include_router(notifications_router, prefix=API_V1)
app.include_router(comments_router, prefix=API_V1)
app.include_router(supplier_intelligence_router, prefix=API_V1)
app.include_router(suppliers_router, prefix=API_V1)
app.include_router(executive_router, prefix=API_V1)
app.include_router(api_platform_router, prefix=API_V1)
app.include_router(regulatory_router, prefix=API_V1)
app.include_router(disclosure_router, prefix=API_V1)
app.include_router(due_diligence_router, prefix=API_V1)
app.include_router(copilot_router, prefix=API_V1)
app.include_router(external_intelligence_router, prefix=API_V1)
app.include_router(operations_router, prefix=API_V1)
app.include_router(supplier_portal_router, prefix=API_V1)
app.include_router(supplier_portal_internal_router, prefix=API_V1)
app.include_router(agent_monitoring_router, prefix=API_V1)
app.include_router(surveillance_router, prefix=API_V1)
