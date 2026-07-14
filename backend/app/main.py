"""
EIOS Backend — FastAPI Application Entry Point

Clean Architecture: Interfaces layer wires up the HTTP transport.
Domain and Application layers have no knowledge of FastAPI.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import (
    MetricsCounterMiddleware,
    RateLimiterMiddleware,
    RequestBodySizeLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from infrastructure.embeddings.deps import init_embedding_provider
from infrastructure.llm.deps import init_llm_provider
from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware
from interfaces.api.routers import (
    activity_chain_router,
    agent_monitoring_router,
    agents_router,
    ai_governance_router,
    api_platform_router,
    assessments_benchmark_router,
    assessments_compliance_router,
    assessments_router,
    audit_router,
    auth_router,
    automations_router,
    board_signoff_router,
    comments_router,
    commercial_router,
    contractual_assurance_router,
    copilot_router,
    corrective_action_plan_router,
    dashboard_router,
    dd_governance_public_router,
    dd_governance_router,
    disclosure_router,
    dpp_router,
    due_diligence_router,
    effectiveness_router,
    enterprise_router,
    erp_router,
    esap_export_router,
    evaluation_router,
    evidences_router,
    executive_router,
    external_intelligence_router,
    financial_esg_router,
    findings_router,
    frameworks_router,
    ghg_router,
    grievance_router,
    health_router,
    impact_assessment_router,
    integrations_router,
    knowledge_router,
    m46_3_router,
    material_router,
    metrics_router,
    mfa_router,
    network_router,
    news_router,
    rag_router,
    documents_router,
    company_intelligence_router,
    scenario_router,
    notifications_router,
    operating_system_router,
    operations_router,
    organizations_router,
    pipeline_router,
    prioritization_router,
    product_router,
    readiness_router,
    recommendations_router,
    region_router,
    regulatory_change_router,
    regulatory_radar_router,
    regulatory_reporting_router,
    regulatory_router,
    remedy_cases_router,
    remedy_grievance_router,
    remedy_report_router,
    reports_router,
    risks_router,
    scope3_router,
    scoping_router,
    sector_intelligence_router,
    sector_risk_register_router,
    sectors_router,
    security_audit_router,
    self_improvement_router,
    sme_support_router,
    stakeholders_public_router,
    stakeholders_router,
    strategy_router,
    supplier_assessment_public_router,
    supplier_assessment_router,
    supplier_extensions_router,
    supplier_intelligence_router,
    supplier_portal_internal_router,
    supplier_portal_router,
    supplier_twin_router,
    suppliers_router,
    supply_chain_compliance_router,
    supply_chain_events_router,
    surveillance_router,
    sustainability_router,
    threshold_monitor_router,
    users_router,
    workflow_context_router,
    workflows_router,
)
from interfaces.api.routers.demo import router as demo_router
from shared.config import settings

# ── Background tasks ──────────────────────────────────────────────────────────

_overdue_task: asyncio.Task | None = None
_webhook_recovery_task: asyncio.Task | None = None
_intelligence_scheduler_task: asyncio.Task | None = None
_agent_scheduler_task: asyncio.Task | None = None
_outbox_task: asyncio.Task | None = None
_consumer_task: asyncio.Task | None = None


async def _check_overdue_loop() -> None:
    """
    Runs every 6 hours. Fires ACTION_OVERDUE notifications for past-due recommendations.

    Query strategy: single JOIN per batch (recs + user in one round-trip).
    Processes in batches of 500 to avoid loading the full table into memory.
    Passes pre-fetched notification_preferences to notify() to eliminate the
    second per-row user lookup inside the service.
    Total DB cost: ceil(overdue_count / 500) queries + 1 dedupe-check + 1 INSERT per new notif.
    """
    from application import notification_service
    from domain.enums import NotificationType
    from infrastructure.persistence.database import AsyncSessionFactory
    from infrastructure.persistence.repositories.recommendation import SQLRecommendationRepository

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

from infrastructure.observability.tracing import OtelStructlogProcessor  # noqa: E402

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        OtelStructlogProcessor(),  # M46: inject trace_id + span_id into every log line
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

    logger.info("eios_startup", environment=settings.environment, version="0.23.0")

    # M46 — OTel tracing (must run before any requests are served)
    from infrastructure.observability.tracing import configure_tracing  # noqa: PLC0415

    configure_tracing(app)

    from infrastructure.kafka.producer import init_kafka_producer  # noqa: PLC0415
    from infrastructure.redis.blacklist import init_redis_blacklist  # noqa: PLC0415
    from infrastructure.redis.client import init_redis  # noqa: PLC0415

    await init_redis()
    await init_redis_blacklist()
    await init_kafka_producer()
    logger.info("kafka_ready", servers=settings.kafka_bootstrap_servers)

    # Wire production SSO validators (M45.1 — G-002)
    from infrastructure.sso.oidc_validator import ProductionOIDCValidator  # noqa: PLC0415
    from infrastructure.sso.saml_validator import ProductionSAMLValidator  # noqa: PLC0415

    app.state.saml_validator = ProductionSAMLValidator()
    app.state.oidc_validator = ProductionOIDCValidator()
    logger.info("sso_validators_ready")

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
    from application.supplier_portal.questionnaire_service import (
        seed_builtin_templates,  # noqa: PLC0415
    )

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

    from application.agent_monitoring.scheduler import run_agent_scheduler  # noqa: PLC0415
    from application.external_intelligence.scheduler import (
        run_intelligence_scheduler,  # noqa: PLC0415
    )

    global \
        _overdue_task, \
        _webhook_recovery_task, \
        _intelligence_scheduler_task, \
        _agent_scheduler_task, \
        _outbox_task, \
        _consumer_task
    _overdue_task = asyncio.create_task(_check_overdue_loop())
    logger.info("overdue_task_started")
    _webhook_recovery_task = asyncio.create_task(run_webhook_recovery_loop())
    logger.info("webhook_recovery_task_started")
    _intelligence_scheduler_task = asyncio.create_task(run_intelligence_scheduler())
    logger.info("intelligence_scheduler_started")
    _agent_scheduler_task = asyncio.create_task(run_agent_scheduler())
    logger.info("agent_scheduler_started")

    # M5 — Supply Chain Event Bus
    from application.supply_chain.handlers import SupplyChainHandlers  # noqa: PLC0415
    from infrastructure.kafka.consumer import get_kafka_consumer  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415

    _sc_consumer = get_kafka_consumer()
    _sc_handlers = SupplyChainHandlers(AsyncSessionFactory)
    _sc_handlers.register_all(_sc_consumer)
    await _sc_consumer.start()
    logger.info("supply_chain_consumer_started")

    async def _outbox_loop() -> None:
        from application.supply_chain.outbox import OutboxPublisher  # noqa: PLC0415

        while True:
            try:
                async with AsyncSessionFactory() as _session:
                    publisher = OutboxPublisher(_session, None)  # type: ignore[arg-type]
                    count = await publisher.run_once()
                    if count:
                        logger.info("outbox_published", count=count)
            except Exception as _exc:
                logger.error("outbox_loop_error", error=str(_exc))
            await asyncio.sleep(settings.kafka_outbox_poll_interval_s)

    async def _consumer_loop() -> None:
        from infrastructure.kafka.consumer import get_kafka_consumer as _get  # noqa: PLC0415

        _c = _get()
        await _c.consume_loop(on_event_log=None)

    _outbox_task = asyncio.create_task(_outbox_loop())
    _consumer_task = asyncio.create_task(_consumer_loop())
    logger.info("supply_chain_event_bus_started")

    yield

    if _outbox_task is not None:
        _outbox_task.cancel()
    if _consumer_task is not None:
        _consumer_task.cancel()
    await _sc_consumer.stop()

    if _overdue_task is not None:
        _overdue_task.cancel()
    if _webhook_recovery_task is not None:
        _webhook_recovery_task.cancel()
    if _intelligence_scheduler_task is not None:
        _intelligence_scheduler_task.cancel()
    if _agent_scheduler_task is not None:
        _agent_scheduler_task.cancel()

    from infrastructure.kafka.producer import close_kafka_producer  # noqa: PLC0415
    from infrastructure.redis.blacklist import close_redis_blacklist  # noqa: PLC0415
    from infrastructure.redis.client import close_redis  # noqa: PLC0415

    await close_redis()
    await close_redis_blacklist()
    await close_kafka_producer()
    logger.info("eios_shutdown")


# ── FastAPI application ────────────────────────────────────────────────────────

app = FastAPI(
    title="EIOS — Enterprise Intelligence Operating System",
    description="ESG Due Diligence and Risk Intelligence Platform API",
    version="0.22.0",
    lifespan=lifespan,
    # Hide docs in production — expose via VPN or behind auth proxy if needed
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── Middleware stack (applied in reverse registration order) ───────────────────
# Execution order: RequestID → RequestLogging → SecurityHeaders → MetricsCounter → CORS → route

app.add_middleware(MetricsCounterMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestBodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
# M47: region enforcement runs after auth sets request.state.organization_id
app.add_middleware(RegionEnforcementMiddleware)

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
app.include_router(demo_router, prefix=API_V1)
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
app.include_router(network_router, prefix=API_V1)
app.include_router(operating_system_router, prefix=API_V1)
app.include_router(enterprise_router)
app.include_router(ai_governance_router, prefix=API_V1)
app.include_router(sustainability_router, prefix=API_V1)
app.include_router(financial_esg_router, prefix=API_V1)
app.include_router(strategy_router, prefix=API_V1)
app.include_router(mfa_router, prefix=API_V1)
app.include_router(ghg_router, prefix=API_V1)
app.include_router(m46_3_router, prefix=API_V1)
app.include_router(region_router, prefix=API_V1)
app.include_router(regulatory_reporting_router, prefix=API_V1)
app.include_router(integrations_router, prefix=API_V1)
app.include_router(commercial_router, prefix=API_V1)
app.include_router(security_audit_router, prefix=API_V1)
app.include_router(supplier_twin_router, prefix=API_V1)
app.include_router(supplier_extensions_router, prefix=API_V1)
app.include_router(material_router, prefix=API_V1)
app.include_router(product_router, prefix=API_V1)
app.include_router(dpp_router, prefix=API_V1)
app.include_router(supply_chain_events_router, prefix=API_V1)
app.include_router(erp_router, prefix=API_V1)
app.include_router(supply_chain_compliance_router, prefix=API_V1)
app.include_router(scope3_router, prefix=API_V1)
app.include_router(sector_risk_register_router, prefix=API_V1)
app.include_router(news_router, prefix=API_V1)
app.include_router(rag_router, prefix=API_V1)
app.include_router(documents_router, prefix=API_V1)
app.include_router(company_intelligence_router, prefix=API_V1)
app.include_router(scenario_router, prefix=API_V1)
app.include_router(automations_router, prefix=API_V1)
app.include_router(pipeline_router, prefix=API_V1)
app.include_router(grievance_router, prefix=API_V1)
app.include_router(prioritization_router, prefix=API_V1)
app.include_router(regulatory_change_router, prefix=API_V1)
app.include_router(evaluation_router, prefix=API_V1)
app.include_router(self_improvement_router, prefix=API_V1)
app.include_router(corrective_action_plan_router, prefix=API_V1)
app.include_router(stakeholders_router, prefix=API_V1)
app.include_router(stakeholders_public_router, prefix=API_V1)
app.include_router(dd_governance_router, prefix=API_V1)
app.include_router(dd_governance_public_router, prefix=API_V1)
app.include_router(remedy_cases_router, prefix=API_V1)
app.include_router(remedy_grievance_router, prefix=API_V1)
app.include_router(remedy_report_router, prefix=API_V1)
app.include_router(effectiveness_router, prefix=API_V1)
app.include_router(scoping_router, prefix=API_V1)
app.include_router(activity_chain_router, prefix=API_V1)
app.include_router(contractual_assurance_router, prefix=API_V1)
app.include_router(sme_support_router, prefix=API_V1)
app.include_router(readiness_router, prefix=API_V1)
app.include_router(impact_assessment_router, prefix=API_V1)
app.include_router(board_signoff_router, prefix=API_V1)
app.include_router(supplier_assessment_router, prefix=API_V1)
app.include_router(supplier_assessment_public_router, prefix=API_V1)
app.include_router(esap_export_router, prefix=API_V1)
app.include_router(threshold_monitor_router, prefix=API_V1)
app.include_router(regulatory_radar_router, prefix=API_V1)
app.include_router(workflow_context_router, prefix=API_V1)
