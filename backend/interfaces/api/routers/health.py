"""Health Check Endpoints (M46 — enhanced from M20).

/health          — liveness probe: is the process alive?
/health/ready    — readiness probe: DB + Redis connectivity (returns 503 if either down)
/health/details  — verbose diagnostics: DB pool, replica lag, backup age (admin-only)

Kubernetes / Docker convention:
  liveness:   200 = alive, non-2xx = restart
  readiness:  200 = ready for traffic, 503 = drain from load balancer
"""

import time

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from infrastructure.persistence.database import engine
from interfaces.api.deps import require_admin
from shared.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])

_start_time = time.time()

VERSION = "0.23.0"


# ── Schemas ───────────────────────────────────────────────────────────────────


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


class PoolStats(BaseModel):
    checked_out: int
    overflow: int
    checked_in: int


class DetailsResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    database: ComponentStatus
    redis: ComponentStatus
    redis_blacklist: ComponentStatus
    replica: ComponentStatus
    backup: ComponentStatus
    db_pool: PoolStats | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


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
    """Readiness probe — checks DB and Redis. Returns 503 if either is down."""
    from infrastructure.llm.deps import _provider as llm_provider_singleton  # noqa: PLC0415

    components: dict[str, ComponentStatus] = {}
    overall_ok = True

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = ComponentStatus(status="ok")
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_db_failed", error=str(exc))
        components["database"] = ComponentStatus(status="degraded", detail=str(exc)[:120])
        overall_ok = False

    # ── Redis (rate-limit / session) ──────────────────────────────────────────
    try:
        from infrastructure.redis.client import get_redis  # noqa: PLC0415

        redis = get_redis()
        if redis is not None:
            await redis.ping()
            components["redis"] = ComponentStatus(status="ok")
        else:
            components["redis"] = ComponentStatus(
                status="unconfigured", detail="Redis not connected"
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_redis_failed", error=str(exc))
        components["redis"] = ComponentStatus(status="degraded", detail=str(exc)[:120])
        overall_ok = False

    # ── Redis Blacklist ───────────────────────────────────────────────────────
    try:
        from infrastructure.redis.blacklist import get_redis_blacklist  # noqa: PLC0415

        bl = get_redis_blacklist()
        if bl is not None:
            await bl.ping()
            components["redis_blacklist"] = ComponentStatus(status="ok")
        else:
            components["redis_blacklist"] = ComponentStatus(
                status="unconfigured", detail="Blacklist Redis not connected"
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_redis_blacklist_failed", error=str(exc))
        components["redis_blacklist"] = ComponentStatus(status="degraded", detail=str(exc)[:120])
        overall_ok = False

    # ── LLM provider ─────────────────────────────────────────────────────────
    if llm_provider_singleton is not None:
        components["llm_provider"] = ComponentStatus(
            status="ok",
            detail=f"{settings.llm_provider}/{settings.llm_model}",
        )
    else:
        components["llm_provider"] = ComponentStatus(
            status="unconfigured",
            detail="No LLM API key — agent workflows unavailable",
        )

    body = ReadinessResponse(
        status="ok" if overall_ok else "degraded",
        service="eios-backend",
        version=VERSION,
        components=components,
    )
    return JSONResponse(content=body.model_dump(), status_code=200 if overall_ok else 503)  # type: ignore[return-value]


@router.get(
    "/health/details",
    response_model=DetailsResponse,
    dependencies=[Depends(require_admin)],
    include_in_schema=True,
)
async def health_details() -> DetailsResponse:
    """Verbose diagnostics for ops: DB pool stats, replica lag, backup age (admin only)."""
    import os  # noqa: PLC0415
    from datetime import UTC, datetime  # noqa: PLC0415

    uptime = round(time.time() - _start_time, 1)

    # ── Primary DB ────────────────────────────────────────────────────────────
    db_status = ComponentStatus(status="ok")
    pool_stats: PoolStats | None = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pool = engine.pool
        pool_stats = PoolStats(
            checked_out=pool.checkedout(),
            overflow=pool.overflow(),
            checked_in=pool.checkedin(),
        )
    except Exception as exc:  # noqa: BLE001
        db_status = ComponentStatus(status="degraded", detail=str(exc)[:200])

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_status = ComponentStatus(status="unconfigured")
    try:
        from infrastructure.redis.client import get_redis  # noqa: PLC0415

        r = get_redis()
        if r is not None:
            info = await r.info("server")
            redis_status = ComponentStatus(
                status="ok",
                detail=f"redis {info.get('redis_version', '?')}",
            )
    except Exception as exc:  # noqa: BLE001
        redis_status = ComponentStatus(status="degraded", detail=str(exc)[:120])

    # ── Redis Blacklist ───────────────────────────────────────────────────────
    bl_status = ComponentStatus(status="unconfigured")
    try:
        from infrastructure.redis.blacklist import get_redis_blacklist  # noqa: PLC0415

        bl = get_redis_blacklist()
        if bl is not None:
            info = await bl.info("server")
            bl_status = ComponentStatus(
                status="ok",
                detail=f"redis {info.get('redis_version', '?')} noeviction",
            )
    except Exception as exc:  # noqa: BLE001
        bl_status = ComponentStatus(status="degraded", detail=str(exc)[:120])

    # ── Read Replica ──────────────────────────────────────────────────────────
    replica_status = ComponentStatus(status="not_configured")
    if settings.database_readonly_url:
        try:
            from infrastructure.persistence.database import _readonly_engine  # noqa: PLC0415

            async with _readonly_engine.connect() as conn:
                row = await conn.execute(text("SELECT pg_is_in_recovery()::text, now()::text"))
                is_replica, ts = row.fetchone()
            replica_status = ComponentStatus(
                status="ok",
                detail=f"in_recovery={is_replica} at {ts[:19]}",
            )
        except Exception as exc:  # noqa: BLE001
            replica_status = ComponentStatus(status="degraded", detail=str(exc)[:120])

    # ── Backup freshness ──────────────────────────────────────────────────────
    backup_dir = os.environ.get("BACKUP_DIR", "/var/backups/eios/postgres")
    marker = os.path.join(backup_dir, ".last_backup_timestamp")
    backup_status = ComponentStatus(status="unknown", detail="No backup marker found")
    if os.path.exists(marker):
        try:
            ts_str = open(marker).read().strip()
            last = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            age_h = round((datetime.now(UTC) - last).total_seconds() / 3600, 1)
            ok = age_h < 25
            backup_status = ComponentStatus(
                status="ok" if ok else "stale",
                detail=f"last={ts_str} ({age_h}h ago)",
            )
        except Exception as exc:  # noqa: BLE001
            backup_status = ComponentStatus(status="unknown", detail=str(exc)[:120])

    overall = "ok" if db_status.status == "ok" else "degraded"

    return DetailsResponse(
        status=overall,
        service="eios-backend",
        version=VERSION,
        uptime_seconds=uptime,
        database=db_status,
        redis=redis_status,
        redis_blacklist=bl_status,
        replica=replica_status,
        backup=backup_status,
        db_pool=pool_stats,
    )
