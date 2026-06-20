"""M35 Supplier Auth Service.

Handles all supplier authentication lifecycle:
  invite()          — create invitation + return invite token
  activate()        — accept invitation, set password, create SupplierUser
  login()           — verify credentials, return tokens
  refresh()         — exchange refresh token for new access token
  request_password_reset() — generate reset token, store hashed in DB
  reset_password()  — consume hashed DB token (single-use), update password

Security:
  - Supplier JWTs carry aud=eios-supplier; internal tokens rejected.
  - Password reset tokens are stored as SHA-256 hashes, single-use (used_at).
  - Login lockout after 5 failed attempts for 15 minutes.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

_INVITE_EXPIRY_HOURS = 72
_RESET_EXPIRY_MINUTES = 30

# M35.1 F7 — brute-force lockout constants
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION = timedelta(minutes=15)


def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def invite_supplier_user(
    supplier_id: str,
    email: str,
    role: str,
    invited_by_user_id: str,
    organization_id: str,
    session,
) -> str:
    """Create an invitation record.  Returns the raw invite token (send in email)."""
    from infrastructure.persistence.models.supplier_portal import SupplierInvitationModel

    raw_token = secrets.token_urlsafe(32)
    hashed = _token_hash(raw_token)
    now = datetime.now(UTC)
    expires = now + timedelta(hours=_INVITE_EXPIRY_HOURS)

    model = SupplierInvitationModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        email=email,
        invited_by_user_id=invited_by_user_id,
        token_hash=hashed,
        role=role,
        expires_at=expires,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()

    logger.info(
        "supplier_invitation_created",
        supplier_id=supplier_id,
        email=email,
        role=role,
    )
    return raw_token


async def activate_supplier_user(
    invite_token: str,
    display_name: str,
    password: str,
    session,
) -> tuple[str, str]:
    """Accept an invitation and create a SupplierUser.

    Returns (access_token, refresh_token).
    """
    from infrastructure.persistence.models.supplier_portal import (
        SupplierInvitationModel,
        SupplierUserModel,
    )
    from shared.security import (
        create_supplier_access_token,
        create_supplier_refresh_token,
        hash_password,
    )
    from sqlalchemy import select

    hashed = _token_hash(invite_token)
    now = datetime.now(UTC)

    stmt = select(SupplierInvitationModel).where(
        SupplierInvitationModel.token_hash == hashed,
        SupplierInvitationModel.accepted_at.is_(None),
        SupplierInvitationModel.expires_at > now,
    )
    invitation = (await session.execute(stmt)).scalar_one_or_none()
    if invitation is None:
        raise ValueError("Invalid or expired invitation token")

    # Check if user already exists for this email
    user_stmt = select(SupplierUserModel).where(
        SupplierUserModel.email == invitation.email,
        SupplierUserModel.supplier_id == invitation.supplier_id,
    )
    existing = (await session.execute(user_stmt)).scalar_one_or_none()
    if existing:
        raise ValueError("A user with this email already exists for this supplier")

    supplier_user_id = str(uuid.uuid4())
    user_model = SupplierUserModel(
        id=supplier_user_id,
        supplier_id=invitation.supplier_id,
        email=invitation.email,
        display_name=display_name,
        role=invitation.role,
        is_active=True,
        invited_at=invitation.created_at,
        accepted_at=now,
        password_hash=hash_password(password),
        failed_login_attempts=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )
    session.add(user_model)

    # Mark invitation as accepted
    invitation.accepted_at = now
    invitation.updated_at = now
    await session.flush()

    await _log_activity(
        supplier_id=invitation.supplier_id,
        supplier_user_id=supplier_user_id,
        event_type="invitation_accepted",
        entity_type="supplier_user",
        entity_id=supplier_user_id,
        session=session,
    )

    access_token = create_supplier_access_token(
        supplier_user_id=supplier_user_id,
        email=invitation.email,
        role=invitation.role,
        supplier_id=invitation.supplier_id,
    )
    refresh_token = create_supplier_refresh_token(supplier_user_id)
    return access_token, refresh_token


async def login_supplier_user(
    email: str,
    password: str,
    session,
) -> tuple[str, str]:
    """Verify credentials and return (access_token, refresh_token).

    M35.1 F7: Locks the account for 15 minutes after 5 consecutive failures.
    """
    from infrastructure.persistence.models.supplier_portal import SupplierUserModel
    from shared.security import (
        create_supplier_access_token,
        create_supplier_refresh_token,
        verify_password,
    )
    from sqlalchemy import select

    stmt = select(SupplierUserModel).where(
        SupplierUserModel.email == email,
        SupplierUserModel.is_active.is_(True),
    )
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None:
        raise ValueError("Invalid email or password")

    now = datetime.now(UTC)

    # Check lockout
    if user.locked_until and user.locked_until > now:
        remaining = int((user.locked_until - now).total_seconds() / 60) + 1
        raise ValueError(
            f"Account temporarily locked due to too many failed attempts. "
            f"Try again in {remaining} minute(s)."
        )

    if not user.password_hash or not verify_password(password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = now + _LOCKOUT_DURATION
            logger.warning(
                "supplier_login_locked",
                email=email,
                supplier_id=user.supplier_id,
                attempts=user.failed_login_attempts,
            )
        user.updated_at = now
        await session.flush()
        raise ValueError("Invalid email or password")

    # Successful login — reset lockout state
    user.last_login_at = now
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = now
    await session.flush()

    await _log_activity(
        supplier_id=user.supplier_id,
        supplier_user_id=user.id,
        event_type="login",
        entity_type="supplier_user",
        entity_id=user.id,
        session=session,
    )

    access_token = create_supplier_access_token(
        supplier_user_id=user.id,
        email=user.email,
        role=user.role,
        supplier_id=user.supplier_id,
    )
    refresh_token = create_supplier_refresh_token(user.id)
    return access_token, refresh_token


async def generate_password_reset_token(
    email: str,
    session,
) -> str | None:
    """Generate a DB-backed password reset token (M35.1 F2).

    Returns the raw token to embed in the email, or None if user not found
    (caller always returns 204 — do not reveal existence).

    Previous stateless JWT approach allowed token reuse. This implementation
    stores a SHA-256 hash and marks tokens used_at on consumption.
    """
    from infrastructure.persistence.models.supplier_portal import (
        SupplierPasswordResetTokenModel,
        SupplierUserModel,
    )
    from sqlalchemy import select

    stmt = select(SupplierUserModel).where(
        SupplierUserModel.email == email,
        SupplierUserModel.is_active.is_(True),
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        return None

    raw_token = secrets.token_urlsafe(32)
    hashed = _token_hash(raw_token)
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=_RESET_EXPIRY_MINUTES)

    reset_record = SupplierPasswordResetTokenModel(
        id=str(uuid.uuid4()),
        email=email,
        supplier_id=user.supplier_id,
        token_hash=hashed,
        expires_at=expires,
        used_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(reset_record)
    await session.flush()
    return raw_token


async def reset_password(
    token: str,
    new_password: str,
    session,
) -> None:
    """Apply a new password from a DB-backed reset token (M35.1 F2).

    Token is single-use: used_at is set on first consumption.
    Expired or already-used tokens are rejected.
    """
    from infrastructure.persistence.models.supplier_portal import (
        SupplierPasswordResetTokenModel,
        SupplierUserModel,
    )
    from shared.security import hash_password
    from sqlalchemy import select

    hashed = _token_hash(token)
    now = datetime.now(UTC)

    reset_stmt = select(SupplierPasswordResetTokenModel).where(
        SupplierPasswordResetTokenModel.token_hash == hashed,
        SupplierPasswordResetTokenModel.used_at.is_(None),
        SupplierPasswordResetTokenModel.expires_at > now,
    )
    reset_record = (await session.execute(reset_stmt)).scalar_one_or_none()
    if reset_record is None:
        raise ValueError("Invalid, expired, or already-used reset token")

    # Mark consumed immediately (single-use guarantee)
    reset_record.used_at = now
    reset_record.updated_at = now

    user_stmt = select(SupplierUserModel).where(
        SupplierUserModel.email == reset_record.email,
        SupplierUserModel.supplier_id == reset_record.supplier_id,
        SupplierUserModel.is_active.is_(True),
    )
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    user.password_hash = hash_password(new_password)
    # Reset lockout on successful password change
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = now
    await session.flush()

    await _log_activity(
        supplier_id=user.supplier_id,
        supplier_user_id=user.id,
        event_type="password_reset",
        entity_type="supplier_user",
        entity_id=user.id,
        session=session,
    )


async def _log_activity(
    supplier_id: str,
    supplier_user_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    session,
    metadata: dict | None = None,
) -> None:
    """Append an immutable activity event to supplier_activity_events."""
    import json
    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    now = datetime.now(UTC)
    model = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("supplier_activity_log_failed", error=str(exc))
