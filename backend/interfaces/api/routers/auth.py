from datetime import UTC, datetime

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_factory
from domain.enums import EntityStatus, UserRole
from domain.organization import Organization
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAuditEventRepository,
    SQLOrganizationRepository,
    SQLUserRepository,
)
from interfaces.api.deps import (
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_organization_repo,
    get_user_repo,
    require_admin,
)
from interfaces.api.schemas.auth import (
    ExternalAccessRevokeRequest,
    ExternalAccessTokenRequest,
    ExternalAccessTokenResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
)
from interfaces.api.schemas.user import PatchMeRequest, UserResponse
from shared.config import settings
from shared.rate_limit import rate_limit_auth
from shared.security import (
    blacklist_token,
    create_access_token,
    create_external_audit_token,
    create_mfa_session_token,
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
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> TokenResponse:
    existing = await user_repo.get_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

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

    await audit_repo.save(
        audit_factory.user_registered(
            user_id=saved.id,
            email=saved.email,
            organization_id=saved_org.id,
        )
    )

    logger.info(
        "user_registered", user_id=saved.id, email=saved.email, organization_id=saved_org.id
    )

    return TokenResponse(
        access_token=create_access_token(saved.id, saved.email, saved.role),
        refresh_token=create_refresh_token(saved.id),
        user=UserResponse.model_validate(saved),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    _rl: None = Depends(rate_limit_auth),
    repo: SQLUserRepository = Depends(get_user_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await repo.get_by_email(body.email)

    if user is None or user.password_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    # Update last_login_at
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
        updated_at=datetime.now(UTC),
        password_hash=user.password_hash,
        last_login_at=datetime.now(UTC),
    )
    saved = await repo.save(updated)
    await audit_repo.save(audit_factory.user_authenticated(user_id=saved.id, email=saved.email))
    logger.info("user_login", user_id=saved.id, email=saved.email)

    # Check MFA status from DB (UserModel field, not domain object which may not have it yet)
    mfa_row = await session.execute(
        text("SELECT mfa_enabled FROM users WHERE id = :user_id"),
        {"user_id": saved.id},
    )
    mfa_result = mfa_row.fetchone()
    mfa_enabled = bool(mfa_result[0]) if mfa_result else False

    if mfa_enabled:
        mfa_session_token = create_mfa_session_token(saved.id)
        return LoginResponse(mfa_required=True, mfa_session_token=mfa_session_token)

    return LoginResponse(
        access_token=create_access_token(saved.id, saved.email, saved.role),
        refresh_token=create_refresh_token(saved.id),
        user=UserResponse.model_validate(saved),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    body: RefreshRequest,
    repo: SQLUserRepository = Depends(get_user_repo),
) -> RefreshResponse:
    """Rotate refresh token: invalidates old token, issues new access + refresh pair."""
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Invalidate the old refresh token (rotation)
    old_jti = payload.get("jti")
    if old_jti:
        await blacklist_token(old_jti, ttl_seconds=settings.refresh_token_expire_days * 86400)

    return RefreshResponse(
        access_token=create_access_token(user.id, user.email, user.role),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke the provided refresh token. Access token expires naturally (15 min)."""
    try:
        payload = decode_token(body.refresh_token)
        jti = payload.get("jti")
        if jti:
            await blacklist_token(jti, ttl_seconds=settings.refresh_token_expire_days * 86400)
    except jwt.InvalidTokenError:
        pass  # Treat invalid tokens as already revoked
    logger.info("user_logout", user_id=current_user.id)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def patch_me(
    body: PatchMeRequest,
    current_user: User = Depends(get_current_user),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> UserResponse:
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.notification_preferences is not None:
        patch = body.notification_preferences.model_dump(exclude_none=True)
        current_user.notification_preferences = {
            **current_user.notification_preferences,
            **patch,
        }
    saved = await user_repo.save(current_user)
    return UserResponse.model_validate(saved)


# ── M45.1 External Auditor Access (G-017) ────────────────────────────────────


@router.post(
    "/external-access/token",
    response_model=ExternalAccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_external_audit_token(
    body: ExternalAccessTokenRequest,
    current_user: User = Depends(require_admin),
) -> ExternalAccessTokenResponse:
    """Issue a 72h scoped read-only token for an external auditor.

    ADMIN-only.  The token is not tied to a user account — it identifies
    the org and a human-readable label (e.g. audit firm name).
    No refresh token is issued.  Revoke with POST /auth/external-access/revoke.
    """
    import uuid as _uuid  # noqa: PLC0415
    from datetime import timedelta  # noqa: PLC0415

    token_id = str(_uuid.uuid4())
    org_id = body.org_id or current_user.organization_id
    token = create_external_audit_token(
        token_id=token_id,
        org_id=org_id,
        label=body.label,
        issued_by=current_user.id,
    )
    expires_at = datetime.now(UTC) + timedelta(hours=settings.external_audit_token_expire_hours)

    logger.info(
        "external_audit_token_issued",
        token_id=token_id,
        org_id=org_id,
        label=body.label,
        issued_by=current_user.id,
    )

    return ExternalAccessTokenResponse(
        token=token,
        token_id=token_id,
        label=body.label,
        org_id=org_id,
        expires_at=expires_at,
    )


@router.post("/external-access/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_external_audit_token(
    body: ExternalAccessRevokeRequest,
    current_user: User = Depends(require_admin),
) -> None:
    """Revoke an external audit token by its token_id (which equals the jti).

    ADMIN-only.  The token is immediately blacklisted in Redis.
    """
    ttl = settings.external_audit_token_expire_hours * 3600
    await blacklist_token(body.token_id, ttl_seconds=ttl)
    logger.info(
        "external_audit_token_revoked",
        token_id=body.token_id,
        revoked_by=current_user.id,
    )
