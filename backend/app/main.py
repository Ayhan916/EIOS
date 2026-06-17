"""
EIOS Backend — FastAPI Application Entry Point

Clean Architecture: Interfaces layer wires up the HTTP transport.
Domain and Application layers have no knowledge of FastAPI.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware import (
    MetricsCounterMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from infrastructure.embeddings.deps import init_embedding_provider
from infrastructure.llm.deps import init_llm_provider
from interfaces.api.routers import (
    agents_router,
    assessments_benchmark_router,
    assessments_compliance_router,
    assessments_router,
    audit_router,
    auth_router,
    evidences_router,
    findings_router,
    frameworks_router,
    health_router,
    knowledge_router,
    metrics_router,
    organizations_router,
    recommendations_router,
    reports_router,
    risks_router,
    sector_intelligence_router,
    sectors_router,
    workflows_router,
)
from shared.config import settings

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

    if settings.anthropic_api_key or settings.openai_api_key:
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

    yield
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
