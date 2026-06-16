"""
EIOS Backend — FastAPI Application Entry Point

Clean Architecture: Interfaces layer wires up the HTTP transport.
Domain and Application layers have no knowledge of FastAPI.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infrastructure.embeddings.deps import init_embedding_provider
from infrastructure.llm.deps import init_llm_provider
from interfaces.api.routers import (
    agents_router,
    assessments_compliance_router,
    assessments_router,
    audit_router,
    auth_router,
    evidences_router,
    findings_router,
    frameworks_router,
    health_router,
    knowledge_router,
    organizations_router,
    recommendations_router,
    reports_router,
    risks_router,
    sectors_router,
    workflows_router,
)
from shared.config import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
        if not settings.is_development
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

API_V1 = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("eios_startup", environment=settings.environment)
    init_embedding_provider()
    logger.info("embedding_provider_ready", model=settings.embedding_model)
    if settings.anthropic_api_key or settings.openai_api_key:
        init_llm_provider()
        logger.info("llm_provider_ready", provider=settings.llm_provider, model=settings.llm_model)
    else:
        logger.warning("llm_provider_not_configured", detail="Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable agent runs")
    yield
    logger.info("eios_shutdown")


app = FastAPI(
    title="EIOS — Enterprise Intelligence Operating System",
    description="ESG Due Diligence and Risk Intelligence Platform API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=str(request.url), error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(health_router)
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
app.include_router(reports_router, prefix=API_V1)
