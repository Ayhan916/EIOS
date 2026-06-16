"""
Health Check Endpoints

/health        — liveness probe: is the process alive?
/health/ready  — readiness probe: can we serve traffic? (DB + provider checks)

Kubernetes / Docker health check convention:
  - liveness: 200 = alive, any non-2xx = restart
  - readiness: 200 = ready to receive traffic, 503 = not ready (remove from LB)
"""

import time

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from infrastructure.persistence.database import engine
from shared.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])

_start_time = time.time()

VERSION = "0.20.0"


class LivenessResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: float


class ComponentStatus(BaseModel):
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    components: dict[str, ComponentStatus]


@router.get("/health", response_model=LivenessResponse, include_in_schema=True)
async def liveness() -> LivenessResponse:
    """Liveness probe — returns 200 if the process is running."""
    return LivenessResponse(
        status="ok",
        service="eios-backend",
        version=VERSION,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    include_in_schema=True,
)
async def readiness() -> ReadinessResponse:
    """
    Readiness probe — checks DB connectivity and provider configuration.
    Returns 503 if any critical component is unavailable.
    """
    from infrastructure.llm.deps import _provider as llm_provider_singleton  # lazy to avoid circular

    components: dict[str, ComponentStatus] = {}
    overall_ok = True

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = ComponentStatus(status="ok")
    except Exception as exc:
        logger.warning("health_db_check_failed", error=str(exc))
        components["database"] = ComponentStatus(
            status="degraded", detail=str(exc)[:120]
        )
        overall_ok = False

    # LLM provider
    if llm_provider_singleton is not None:
        components["llm_provider"] = ComponentStatus(
            status="ok",
            detail=f"{settings.llm_provider}/{settings.llm_model}",
        )
    else:
        components["llm_provider"] = ComponentStatus(
            status="unconfigured",
            detail="No LLM API key set. Agent workflows will be unavailable.",
        )

    body = ReadinessResponse(
        status="ok" if overall_ok else "degraded",
        service="eios-backend",
        version=VERSION,
        components=components,
    )
    return JSONResponse(content=body.model_dump(), status_code=200 if overall_ok else 503)  # type: ignore[return-value]
