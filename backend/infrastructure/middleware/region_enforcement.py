"""M47 — Region Enforcement Middleware + Dependency.

Two-layer enforcement:

1. RegionEnforcementMiddleware (advisory audit log):
   Runs AFTER the route handler via `call_next`. Reads `request.state.organization_id`
   and `request.state.data_residency` set by `get_current_user`, then writes a
   DataResidencyAuditLogModel entry in a background task.
   Never blocks requests — pure observability.

2. enforce_data_residency FastAPI dependency (strict mode):
   Runs AS PART of FastAPI's dependency resolution (before the handler body).
   Returns HTTP 451 Unavailable For Legal Reasons when:
     - REGION_ENFORCEMENT_STRICT=true
     - The org's declared region differs from this instance's region
   Add to a router via: `dependencies=[Depends(enforce_data_residency)]`

Design rationale:
  - Advisory middleware: transparent, no per-endpoint opt-in needed.
  - Strict dependency: opt-in per router, runs before any DB writes.
    This is correct — middleware running after `call_next` cannot un-commit
    already-written data, so strict enforcement must happen before the handler.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from infrastructure.routing.region_router import region_router
from shared.config import settings

logger = structlog.get_logger(__name__)

_SKIP_PATHS = frozenset({"/health", "/metrics", "/docs", "/redoc", "/openapi.json"})


# ─────────────────────────────────────────────────────────────────────────────
# Advisory middleware — post-handler audit logging
# ─────────────────────────────────────────────────────────────────────────────


class RegionEnforcementMiddleware(BaseHTTPMiddleware):
    """Log cross-region access events AFTER the handler completes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS or request.url.path.startswith("/metrics"):
            return await call_next(request)

        # Execute the handler (auth deps run here, setting request.state)
        response = await call_next(request)

        org_id: str | None = getattr(request.state, "organization_id", None)
        data_residency: str | None = getattr(request.state, "data_residency", None)
        user_id: str | None = getattr(request.state, "user_id", None)

        if not org_id:
            return response

        is_local = region_router.is_local_region(data_residency)
        event_type = (
            "local_access"
            if is_local
            else ("region_unknown" if not data_residency else "cross_region_access")
        )

        if event_type != "local_access":
            logger.info(
                "region_cross_access",
                org_id=org_id,
                org_region=region_router.canonical(data_residency),
                instance_region=settings.instance_region.upper(),
                event_type=event_type,
                path=request.url.path,
            )
            asyncio.create_task(
                _write_audit_log(
                    org_id=org_id,
                    user_id=user_id,
                    request_path=str(request.url.path),
                    request_method=request.method,
                    org_region=region_router.canonical(data_residency) if data_residency else None,
                    instance_region=settings.instance_region.upper(),
                    event_type=event_type,
                    ip_address=_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                )
            )

        return response


# ─────────────────────────────────────────────────────────────────────────────
# Strict enforcement — FastAPI dependency (opt-in per router)
# ─────────────────────────────────────────────────────────────────────────────


async def enforce_data_residency(
    request: Request,
    session: AsyncSession = Depends(lambda: None),  # real dep injected at use site
) -> None:
    """FastAPI dependency that enforces data residency in strict mode.

    When REGION_ENFORCEMENT_STRICT=true, returns HTTP 451 if the authenticated
    organization's declared region doesn't match this instance's region.

    Reads organization_id from `request.state` (set by `get_current_user`).
    Must be declared AFTER `get_current_user` in the dependency chain.

    Usage:
        router = APIRouter(dependencies=[Depends(enforce_data_residency_dep)])

    See `get_enforce_data_residency` for the concrete FastAPI dep that includes
    the DB session.
    """
    if not settings.region_enforcement_strict:
        return

    org_id: str | None = getattr(request.state, "organization_id", None)
    data_residency: str | None = getattr(request.state, "data_residency", None)

    if not org_id:
        return

    if not region_router.is_local_region(data_residency):
        canonical = region_router.canonical(data_residency)
        raise HTTPException(
            status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            detail={
                "error": "data_residency_violation",
                "message": (
                    f"This instance serves region '{settings.instance_region.upper()}'. "
                    f"Your organization is registered in region '{canonical}'. "
                    f"Please connect to the '{canonical}' EIOS endpoint."
                ),
                "org_region": canonical,
                "instance_region": settings.instance_region.upper(),
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Background DB write
# ─────────────────────────────────────────────────────────────────────────────


async def _write_audit_log(
    *,
    org_id: str | None,
    user_id: str | None,
    request_path: str,
    request_method: str,
    org_region: str | None,
    instance_region: str,
    event_type: str,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    try:
        from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
        from infrastructure.persistence.models.region import (
            DataResidencyAuditLogModel,  # noqa: PLC0415
        )

        now = datetime.now(UTC)
        entry = DataResidencyAuditLogModel(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=user_id,
            request_path=request_path,
            request_method=request_method,
            org_region=org_region,
            instance_region=instance_region,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
        )
        async with AsyncSessionFactory() as session, session.begin():
            session.add(entry)
    except Exception as exc:
        logger.error("region_audit_write_failed", error=str(exc))


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
