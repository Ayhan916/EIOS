from datetime import datetime, timezone

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from domain.enums import EntityStatus, UserRole
from domain.organization import Organization
from domain.user import User
from infrastructure.persistence.repositories import SQLOrganizationRepository, SQLUserRepository
from interfaces.api.deps import get_current_user, get_organization_repo, get_user_repo
from shared.rate_limit import rate_limit_auth
from interfaces.api.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from interfaces.api.schemas.user import UserResponse
from shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    _rl: None = Depends(rate_limit_auth),
    user_repo: SQLUserRepository = Depends(get_user_repo),
    org_repo: SQLOrganizationRepository = Depends(get_organization_repo),
) -> TokenResponse:
    existing = await user_repo.get_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create organization — every new registration bootstraps their own tenant
    org = Organization(
        name=body.organization_name,
        status=EntityStatus.ACTIVE,
    )
    saved_org = await org_repo.save(org)

    user = User(
        email=body.email,
        display_name=body.display_name,
        role=UserRole.ADMIN.value,
        organization_id=saved_org.id,
        is_active=True,
        status=EntityStatus.ACTIVE,
        password_hash=hash_password(body.password),
    )
    saved = await user_repo.save(user)

    logger.info(
        "user_registered",
        user_id=saved.id,
        email=saved.email,
        organization_id=saved_org.id,
    )

    return TokenResponse(
        access_token=create_access_token(saved.id, saved.email, saved.role),
        refresh_token=create_refresh_token(saved.id),
        user=UserResponse.model_validate(saved),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    _rl: None = Depends(rate_limit_auth),
    repo: SQLUserRepository = Depends(get_user_repo),
) -> TokenResponse:
    user = await repo.get_by_email(body.email)

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive",
        )

    updated = User(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        organization_id=user.organization_id,
        is_active=user.is_active,
        status=user.status,
        version=user.version,
        owner=user.owner,
        created_by=user.created_by,
        updated_by=user.updated_by,
        created_at=user.created_at,
        updated_at=datetime.now(timezone.utc),
        password_hash=user.password_hash,
        last_login_at=datetime.now(timezone.utc),
    )
    saved = await repo.save(updated)

    logger.info("user_login", user_id=saved.id, email=saved.email)

    return TokenResponse(
        access_token=create_access_token(saved.id, saved.email, saved.role),
        refresh_token=create_refresh_token(saved.id),
        user=UserResponse.model_validate(saved),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    body: RefreshRequest,
    repo: SQLUserRepository = Depends(get_user_repo),
) -> AccessTokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.email, user.role),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
