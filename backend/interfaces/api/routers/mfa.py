"""
M45 MFA Router — TOTP setup, confirmation, verification, and disable.

Endpoints:
  POST /auth/mfa/setup    → Initiate MFA (generates secret + backup codes)
  POST /auth/mfa/confirm  → Activate MFA (verifies first TOTP code)
  POST /auth/mfa/verify   → Complete MFA login challenge
  POST /auth/mfa/disable  → Disable MFA using a backup code
  GET  /auth/mfa/status   → Return current MFA state for the authenticated user
"""

from __future__ import annotations

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from application.mfa.service import confirm_mfa, disable_mfa, setup_mfa, verify_mfa_code
from domain.user import User
from interfaces.api.deps import get_current_user, get_db
from interfaces.api.schemas.auth import TokenResponse
from shared.config import settings
from shared.rate_limit import rate_limit_auth
from shared.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


class MFASetupResponse(BaseModel):
    otp_uri: str
    backup_codes: list[str]
    message: str = "Scan the QR code with your authenticator app, then call /auth/mfa/confirm"


class MFAConfirmRequest(BaseModel):
    code: str


class MFAVerifyRequest(BaseModel):
    mfa_session_token: str
    code: str


class MFADisableRequest(BaseModel):
    backup_code: str


class MFAStatusResponse(BaseModel):
    mfa_enabled: bool
    mfa_confirmed_at: str | None


@router.post("/setup", response_model=MFASetupResponse)
async def setup(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MFASetupResponse:
    """Generate a new TOTP secret and backup codes. MFA is NOT active until /confirm."""
    result = await setup_mfa(current_user.id, current_user.email, session)
    return MFASetupResponse(otp_uri=result.otp_uri, backup_codes=result.backup_codes)


@router.post("/confirm", status_code=status.HTTP_200_OK)
async def confirm(
    body: MFAConfirmRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Verify the first TOTP code to activate MFA on the account."""
    ok = await confirm_mfa(current_user.id, body.code, session)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Make sure your authenticator app is synced.",
        )
    logger.info("mfa_activated", user_id=current_user.id)
    return {"message": "MFA activated successfully"}


@router.post("/verify", response_model=TokenResponse)
async def verify(
    body: MFAVerifyRequest,
    _rl: None = Depends(rate_limit_auth),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Complete the MFA login challenge. Returns full access + refresh tokens."""
    try:
        payload = decode_token(body.mfa_session_token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA session expired. Please log in again.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA session token.",
        ) from exc

    if payload.get("type") != "mfa_challenge":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    user_id: str = payload["sub"]
    jti: str = payload.get("jti", "")

    # Enforce rate limiting per user: track failed attempts in Redis
    from infrastructure.redis.client import get_redis

    redis = get_redis()
    lockout_key = f"mfa_lockout:{user_id}"
    if redis is not None:
        attempts = await redis.get(lockout_key)
        if attempts and int(attempts) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed MFA attempts. Try again in 15 minutes.",
                headers={"Retry-After": "900"},
            )

    ok = await verify_mfa_code(user_id, body.code, session)
    if not ok:
        if redis is not None:
            await redis.incr(lockout_key)
            await redis.expire(lockout_key, 900)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code.",
        )

    # Clear lockout counter on success
    if redis is not None:
        await redis.delete(lockout_key)

    # Consume the MFA session token (single-use)
    if jti:
        await blacklist_token(jti, ttl_seconds=settings.mfa_session_expire_minutes * 60)

    # Fetch user for token generation
    from infrastructure.persistence.repositories.user import SQLUserRepository

    user_repo = SQLUserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    from interfaces.api.schemas.user import UserResponse

    logger.info("mfa_login_complete", user_id=user_id)
    return TokenResponse(
        access_token=create_access_token(user.id, user.email, user.role),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


@router.post("/disable", status_code=status.HTTP_200_OK)
async def disable(
    body: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Disable MFA using a backup code."""
    ok = await disable_mfa(current_user.id, body.backup_code, session)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup code.",
        )
    logger.info("mfa_disabled_by_user", user_id=current_user.id)
    return {"message": "MFA disabled successfully"}


@router.get("/status", response_model=MFAStatusResponse)
async def mfa_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MFAStatusResponse:
    """Return the MFA state for the current user."""
    from sqlalchemy import text

    row = await session.execute(
        text("SELECT mfa_enabled, mfa_confirmed_at FROM users WHERE id = :user_id"),
        {"user_id": current_user.id},
    )
    result = row.fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return MFAStatusResponse(
        mfa_enabled=bool(result[0]),
        mfa_confirmed_at=result[1].isoformat() if result[1] else None,
    )
