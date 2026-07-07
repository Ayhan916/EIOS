"""Demo Mode API — activate/reset/status endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.demo.seed import (
    DEMO_ORG_ID,
    DEMO_USER_EMAIL,
    ensure_demo_data,
    is_demo_seeded,
    reset_demo_data,
)
from interfaces.api.deps import get_db, require_admin
from interfaces.api.schemas.auth import TokenResponse
from interfaces.api.schemas.user import UserResponse
from shared.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/demo", tags=["demo"])
logger = structlog.get_logger(__name__)


class DemoStatusResponse(BaseModel):
    seeded: bool
    demo_org_id: str
    demo_user_email: str


@router.get("/status", response_model=DemoStatusResponse)
async def demo_status(
    session: AsyncSession = Depends(get_db),
) -> DemoStatusResponse:
    """Check whether demo data is already seeded."""
    seeded = await is_demo_seeded(session)
    return DemoStatusResponse(
        seeded=seeded,
        demo_org_id=DEMO_ORG_ID,
        demo_user_email=DEMO_USER_EMAIL,
    )


@router.post("/activate", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def activate_demo(
    _admin=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Seed demo data (if not present) and return a demo JWT token."""
    try:
        demo_user = await ensure_demo_data(session)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("demo_activate_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo activation failed: {exc}",
        ) from exc

    logger.info("demo_activated", user_id=demo_user.id)
    return TokenResponse(
        access_token=create_access_token(demo_user.id, demo_user.email, demo_user.role),
        refresh_token=create_refresh_token(demo_user.id),
        user=UserResponse.model_validate(demo_user),
    )


@router.post("/reset", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def reset_demo(
    _admin=Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Wipe demo data and re-seed to initial state. Returns fresh demo token."""
    try:
        demo_user = await reset_demo_data(session)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("demo_reset_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo reset failed: {exc}",
        ) from exc

    logger.info("demo_reset", user_id=demo_user.id)
    return TokenResponse(
        access_token=create_access_token(demo_user.id, demo_user.email, demo_user.role),
        refresh_token=create_refresh_token(demo_user.id),
        user=UserResponse.model_validate(demo_user),
    )
