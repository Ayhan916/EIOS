"""SCIM 2.0 bearer token management (M40.1).

SCIM provisioning from external IdPs (Azure AD, Okta, etc.) must use a
dedicated bearer token, not a user JWT. This module handles lifecycle:

  create  — generates cryptographically random token, stores only SHA-256 hash
  revoke  — soft-delete (is_active=False)
  rotate  — revoke + create in one transaction
  verify  — hash lookup + active/expiry check; updates last_used_at
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.enterprise import SCIMTokenModel

_TOKEN_BYTES = 32          # 256-bit raw token
_DEFAULT_TTL_DAYS = 365    # 1-year default; 0 = no expiry


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _audit(
    session: AsyncSession,
    action: str,
    actor_id: str | None,
    entity_id: str,
    detail: str,
    metadata: dict | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        action=action,
        entity_type="SCIMToken",
        entity_id=entity_id,
        actor_id=actor_id,
        outcome="success",
        detail=detail,
        event_metadata=metadata or {},
    ))


async def create_scim_token(
    enterprise_id: str,
    label: str | None,
    ttl_days: int,
    actor_id: str,
    session: AsyncSession,
) -> tuple[str, SCIMTokenModel]:
    """Create a new SCIM bearer token.

    Returns (raw_token, model). The raw_token is returned ONCE — it is never
    retrievable again. Store it immediately in the IdP configuration.
    """
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=ttl_days) if ttl_days > 0 else None

    token = SCIMTokenModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        token_hash=_hash_token(raw),
        label=label,
        is_active=True,
        expires_at=expires_at,
        last_used_at=None,
        use_count=0,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(token)
    await session.flush()
    await _audit(
        session,
        "scim.token.created",
        actor_id,
        token.id,
        f"SCIM token '{label or token.id}' created for enterprise {enterprise_id}",
        {"enterprise_id": enterprise_id, "ttl_days": ttl_days},
    )
    return raw, token


async def revoke_scim_token(
    token_id: str,
    actor_id: str,
    session: AsyncSession,
) -> bool:
    """Revoke a SCIM token. Returns False if not found."""
    result = await session.execute(
        select(SCIMTokenModel).where(SCIMTokenModel.id == token_id)
    )
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.is_active = False
    token.updated_at = datetime.now(UTC)
    await _audit(
        session,
        "scim.token.revoked",
        actor_id,
        token_id,
        f"SCIM token '{token.label or token_id}' revoked",
        {"enterprise_id": token.enterprise_id},
    )
    return True


async def rotate_scim_token(
    token_id: str,
    new_label: str | None,
    ttl_days: int,
    actor_id: str,
    session: AsyncSession,
) -> tuple[str, SCIMTokenModel] | None:
    """Revoke existing token and issue a replacement in one transaction.

    Returns (new_raw_token, new_model) or None if the old token was not found.
    """
    result = await session.execute(
        select(SCIMTokenModel).where(SCIMTokenModel.id == token_id)
    )
    old = result.scalar_one_or_none()
    if not old:
        return None

    enterprise_id = old.enterprise_id
    label = new_label or old.label

    old.is_active = False
    old.updated_at = datetime.now(UTC)
    await _audit(
        session,
        "scim.token.revoked",
        actor_id,
        token_id,
        f"SCIM token rotated — old token '{old.label or token_id}' revoked",
        {"enterprise_id": enterprise_id, "rotated": True},
    )

    return await create_scim_token(enterprise_id, label, ttl_days, actor_id, session)


async def verify_scim_token(
    raw_token: str,
    session: AsyncSession,
) -> SCIMTokenModel | None:
    """Return the SCIMTokenModel if the token is valid, active, and not expired.

    Also increments use_count and updates last_used_at for auditability.
    Returns None on any failure — callers raise 401.
    """
    token_hash = _hash_token(raw_token)
    result = await session.execute(
        select(SCIMTokenModel).where(SCIMTokenModel.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if not token or not token.is_active:
        return None

    now = datetime.now(UTC)
    if token.expires_at and token.expires_at < now:
        return None

    token.last_used_at = now
    token.use_count += 1
    token.updated_at = now
    return token


async def list_scim_tokens(
    enterprise_id: str,
    session: AsyncSession,
) -> list[SCIMTokenModel]:
    result = await session.execute(
        select(SCIMTokenModel).where(
            SCIMTokenModel.enterprise_id == enterprise_id,
        ).order_by(SCIMTokenModel.created_at.desc())
    )
    return list(result.scalars().all())
