"""
FastAPI dependency injection for EIOS API.

Each dependency provides a repository scoped to the request's database transaction.
The transaction commits at request end (on success) and rolls back on exception.
"""

from collections.abc import AsyncGenerator, Callable, Generator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from domain.enums import UserRole, has_min_role
from domain.user import User
from infrastructure.persistence.database import AsyncSessionFactory, SyncSessionFactory
from infrastructure.persistence.repositories import (
    SQLAgentRunRepository,
    SQLApiKeyRepository,
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLBoardReportRepository,
    SQLCommentRepository,
    SQLEvidenceRepository,
    SQLFindingEvidenceLinkRepository,
    SQLFindingRepository,
    SQLNotificationRepository,
    SQLOrganizationRepository,
    SQLRecommendationRepository,
    SQLReportScheduleRepository,
    SQLReviewActionRepository,
    SQLRiskRepository,
    SQLSectorRepository,
    SQLServiceAccountRepository,
    SQLSupplierRepository,
    SQLSupplierScoreRepository,
    SQLUserRepository,
    SQLWebhookDeliveryRepository,
    SQLWebhookSubscriptionRepository,
    SQLWorkflowJobRepository,
    SQLWorkflowRunRepository,
)
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository
from infrastructure.persistence.repositories.report import SQLReportRepository
from application.api_platform.key_service import hash_api_key, is_api_key_token
from shared.rls import async_set_rls_context
from shared.security import decode_external_audit_token, decode_token, is_token_blacklisted

_bearer = HTTPBearer(auto_error=False)
_bearer_required = HTTPBearer(auto_error=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session, session.begin():
        yield session


def get_sync_db() -> Generator[Session, None, None]:
    """Sync session for strategy services that use session.query() (psycopg2 engine)."""
    with SyncSessionFactory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


async def get_assessment_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAssessmentRepository:
    return SQLAssessmentRepository(session)


async def get_sector_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLSectorRepository:
    return SQLSectorRepository(session)


async def get_finding_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLFindingRepository:
    return SQLFindingRepository(session)


async def get_finding_evidence_link_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLFindingEvidenceLinkRepository:
    return SQLFindingEvidenceLinkRepository(session)


async def get_risk_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLRiskRepository:
    return SQLRiskRepository(session)


async def get_evidence_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLEvidenceRepository:
    return SQLEvidenceRepository(session)


async def get_recommendation_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLRecommendationRepository:
    return SQLRecommendationRepository(session)


async def get_user_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLUserRepository:
    return SQLUserRepository(session)


async def get_agent_run_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAgentRunRepository:
    return SQLAgentRunRepository(session)


async def get_workflow_run_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWorkflowRunRepository:
    return SQLWorkflowRunRepository(session)


async def get_audit_event_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAuditEventRepository:
    return SQLAuditEventRepository(session)


async def get_workflow_job_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWorkflowJobRepository:
    return SQLWorkflowJobRepository(session)


async def get_organization_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLOrganizationRepository:
    return SQLOrganizationRepository(session)


async def get_chunk_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLEvidenceChunkRepository:
    return SQLEvidenceChunkRepository(session)


async def get_notification_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLNotificationRepository:
    return SQLNotificationRepository(session)


async def get_report_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLReportRepository:
    return SQLReportRepository(session)


async def get_comment_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLCommentRepository:
    return SQLCommentRepository(session)


async def get_review_action_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLReviewActionRepository:
    return SQLReviewActionRepository(session)


async def get_supplier_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLSupplierRepository:
    return SQLSupplierRepository(session)


async def get_supplier_score_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLSupplierScoreRepository:
    return SQLSupplierScoreRepository(session)


async def get_api_key_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLApiKeyRepository:
    return SQLApiKeyRepository(session)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repo: SQLUserRepository = Depends(get_user_repo),
    api_key_repo: SQLApiKeyRepository = Depends(get_api_key_repo),
    session: AsyncSession = Depends(get_db),
) -> User:
    _unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise _unauth

    token = credentials.credentials

    # ── API key path ──────────────────────────────────────────────────────────
    if is_api_key_token(token):
        key_hash = hash_api_key(token)
        api_key = await api_key_repo.get_by_hash(key_hash)
        if api_key is None or not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Atomic increment + rate limit check.
        # Increment counters first (resetting expired windows), then check the new
        # values against limits. This is fully atomic at the DB level via a single
        # UPDATE…RETURNING. The counter reflects this request — reject if it exceeded.
        from datetime import UTC, datetime  # noqa: PLC0415
        now = datetime.now(UTC)
        new_min, new_hr = await api_key_repo.atomic_increment_and_get_counts(api_key.id, now)
        if new_min > api_key.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (per-minute)",
                headers={"Retry-After": "60"},
            )
        if new_hr > api_key.rate_limit_per_hour:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded (per-hour)",
                headers={"Retry-After": "3600"},
            )

        # Emit process-level metric
        try:
            from interfaces.api.routers.metrics import counters as _m  # noqa: PLC0415
            _m.record_api_key_request()
        except Exception:  # noqa: BLE001
            pass

        # Attach scopes to request state for require_scope checks
        request.state.api_scopes = set(api_key.scopes)
        request.state.api_key_id = api_key.id

        # Build a synthetic User representing the service account
        # organization_id and is_active are the fields existing endpoints care about
        from domain.enums import EntityStatus, UserRole  # noqa: PLC0415
        from domain.user import User as DomainUser  # noqa: PLC0415
        synthetic = DomainUser(
            id=api_key.service_account_id or api_key.id,
            status=EntityStatus.ACTIVE,
            email="api-key@service",
            display_name=api_key.name,
            role=UserRole.ANALYST,
            organization_id=api_key.organization_id,
            is_active=True,
            password_hash="",
        )
        await async_set_rls_context(session, api_key.organization_id)
        request.state.organization_id = api_key.organization_id
        request.state.user_id = synthetic.id
        request.state.data_residency = await _fetch_data_residency(session, api_key.organization_id)
        return synthetic

    # ── JWT path ──────────────────────────────────────────────────────────────
    # Clear any stale API platform state from request
    request.state.api_scopes = None
    request.state.api_key_id = None

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidAudienceError:
        # Token has a non-standard audience — check if it's an external audit token
        user = await _handle_external_audit_token(token)
        await async_set_rls_context(session, user.organization_id)
        return user
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token blacklist (logout / token rotation)
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await async_set_rls_context(session, user.organization_id)
    request.state.organization_id = user.organization_id
    request.state.user_id = user.id
    request.state.data_residency = await _fetch_data_residency(session, user.organization_id)
    return user


async def _fetch_data_residency(session: AsyncSession, organization_id: str | None) -> str | None:
    """Return the data_residency tag for the given org, or None if unknown."""
    if not organization_id:
        return None
    try:
        from sqlalchemy import select  # noqa: PLC0415
        from infrastructure.persistence.models.organization import OrganizationModel  # noqa: PLC0415
        org = (await session.execute(
            select(OrganizationModel.data_residency).where(OrganizationModel.id == organization_id)
        )).scalar_one_or_none()
        return org  # scalar is the data_residency string or None
    except Exception:
        return None


async def _handle_external_audit_token(token: str) -> User:
    """Decode an external audit JWT and return a synthetic read-only User.

    No database lookup — all identity comes from the verified token payload.
    Raises 401 on invalid/expired/revoked tokens.
    """
    _unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_external_audit_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise _unauth from exc

    if payload.get("type") != "access" or payload.get("role") != "external_auditor":
        raise _unauth

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from domain.enums import EntityStatus, UserRole  # noqa: PLC0415
    from domain.user import User as DomainUser  # noqa: PLC0415

    return DomainUser(
        id=payload["sub"],
        status=EntityStatus.ACTIVE,
        email=payload.get("label", "external-auditor"),
        display_name=payload.get("label"),
        role=UserRole.EXTERNAL_AUDITOR.value,
        organization_id=payload.get("org_id", ""),
        is_active=True,
        password_hash="",
    )


def require_role(min_role: UserRole) -> Callable:
    """Return a FastAPI dependency that enforces a minimum role.

    API key users bypass role checks entirely — their access is governed
    exclusively by scope enforcement (require_scope).  JWT users continue
    to use role-based access control as before.
    """

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        # API key requests: scopes control access, not roles
        if getattr(request.state, "api_key_id", None) is not None:
            return current_user
        if not has_min_role(current_user.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{min_role.value}' or higher is required",
            )
        return current_user

    return _check


require_analyst: Callable = require_role(UserRole.ANALYST)
require_reviewer: Callable = require_role(UserRole.REVIEWER)
require_executive: Callable = require_role(UserRole.EXECUTIVE)
require_admin: Callable = require_role(UserRole.ADMIN)


def require_external_auditor_or_internal(min_internal_role: UserRole = UserRole.VIEWER) -> Callable:
    """Allow external auditors OR internal users with at least min_internal_role.

    Use on read-only endpoints that external audit firms should access (e.g. compliance
    gap lists, risk registers, finding details) while keeping write paths internal-only.
    API key users bypass role checks as usual.
    """

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if getattr(request.state, "api_key_id", None) is not None:
            return current_user
        if current_user.role == UserRole.EXTERNAL_AUDITOR.value:
            return current_user
        if not has_min_role(current_user.role, min_internal_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{min_internal_role.value}' or 'external_auditor' is required"
                ),
            )
        return current_user

    return _check


async def get_board_report_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLBoardReportRepository:
    return SQLBoardReportRepository(session)


async def get_report_schedule_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLReportScheduleRepository:
    return SQLReportScheduleRepository(session)


# ── M30 API Platform repos ────────────────────────────────────────────────────

async def get_service_account_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLServiceAccountRepository:
    return SQLServiceAccountRepository(session)


async def get_webhook_subscription_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWebhookSubscriptionRepository:
    return SQLWebhookSubscriptionRepository(session)


async def get_webhook_delivery_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWebhookDeliveryRepository:
    return SQLWebhookDeliveryRepository(session)


def require_scope(scope: str) -> Callable:
    """FastAPI dependency: pass for JWT users, enforce scope for API-key requests."""

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        api_scopes = getattr(request.state, "api_scopes", None)
        if api_scopes is not None and scope not in api_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {scope}",
            )
        return current_user

    return _check


def scope_gate(read_scope: str, write_scope: str | None = None) -> Callable:
    """Router-level scope dependency.  Checks scope based on HTTP method.

    GET/HEAD/OPTIONS → read_scope
    POST/PATCH/PUT/DELETE → write_scope if provided, else read_scope

    JWT users (api_scopes is None) always pass through — RBAC handles them.
    This is the canonical way to add scope enforcement to a whole router
    without modifying every individual endpoint signature.
    """
    _WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

    async def _check(
        request: Request,
        _: User = Depends(get_current_user),
    ) -> None:
        api_scopes = getattr(request.state, "api_scopes", None)
        if api_scopes is None:
            return  # JWT user — RBAC already handled by require_role
        method = request.method.upper()
        required = (write_scope if write_scope and method in _WRITE_METHODS else read_scope)
        if required not in api_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key missing required scope: {required}",
            )

    return _check


# ── SCIM bearer token dependency (M40.1) ─────────────────────────────────────


async def require_scim_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
):
    """FastAPI dependency for SCIM endpoints.

    Validates the SCIM bearer token (separate from user JWTs).
    Returns the SCIMTokenModel so the endpoint knows which enterprise it belongs to.
    Raises 401 on missing, invalid, expired, or revoked token.
    """
    _unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="SCIM authentication required",
        headers={"WWW-Authenticate": 'Bearer realm="SCIM"'},
    )
    if credentials is None:
        raise _unauth

    from application.enterprise.scim_token_service import verify_scim_token  # noqa: PLC0415
    token = await verify_scim_token(credentials.credentials, session)
    if token is None:
        raise _unauth
    return token
