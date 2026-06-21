"""SCIM 2.0 bearer token management — M40.1 / M40.4.

M40.4 additions:
  - idp_id binding: each token is bound to exactly one IdentityProvider
  - scope: READ_ONLY | PROVISIONING | FULL_ADMIN (default: FULL_ADMIN for back-compat)
  - rotate_scim_token() emits scim.token.rotated (distinct from revoked)
  - list_scim_usage() returns per-enterprise token usage stats
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.enterprise import SCIMTokenModel

_TOKEN_BYTES = 32
_DEFAULT_TTL_DAYS = 365

# Token scope values — ordered from most to least permissive
SCIM_SCOPES = ("FULL_ADMIN", "PROVISIONING", "READ_ONLY")

# Which scopes allow which operations
_WRITE_SCOPES = frozenset({"FULL_ADMIN", "PROVISIONING"})
_READ_SCOPES = frozenset({"FULL_ADMIN", "PROVISIONING", "READ_ONLY"})
_ADMIN_SCOPES = frozenset({"FULL_ADMIN"})


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def can_provision(scope: str) -> bool:
    """True if the scope allows user provisioning (create/update/deactivate)."""
    return scope in _WRITE_SCOPES


def can_read(scope: str) -> bool:
    """True if the scope allows read operations."""
    return scope in _READ_SCOPES


def can_admin(scope: str) -> bool:
    """True if the scope allows admin operations (token mgmt, config)."""
    return scope in _ADMIN_SCOPES


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
    idp_id: str | None = None,
    scope: str = "FULL_ADMIN",
) -> tuple[str, SCIMTokenModel]:
    """Create a new SCIM bearer token.

    idp_id: bind to a specific IdentityProvider (M40.4).
            None for enterprise-wide tokens (backward compat).
    scope: READ_ONLY | PROVISIONING | FULL_ADMIN

    Returns (raw_token, model). The raw_token is returned ONCE only.
    """
    if scope not in SCIM_SCOPES:
        raise ValueError(f"Invalid SCIM scope: {scope!r}. Must be one of {SCIM_SCOPES}")

    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=ttl_days) if ttl_days > 0 else None

    token = SCIMTokenModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        idp_id=idp_id,
        scope=scope,
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
        f"SCIM token '{label or token.id}' created (scope={scope})",
        {"enterprise_id": enterprise_id, "ttl_days": ttl_days, "idp_id": idp_id, "scope": scope},
    )
    return raw, token


async def revoke_scim_token(
    token_id: str,
    actor_id: str,
    session: AsyncSession,
) -> bool:
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
    """Revoke existing token and issue a replacement atomically.

    Emits scim.token.rotated (distinct from scim.token.revoked).
    The new token inherits idp_id and scope from the old token.
    """
    result = await session.execute(
        select(SCIMTokenModel).where(SCIMTokenModel.id == token_id)
    )
    old = result.scalar_one_or_none()
    if not old:
        return None

    enterprise_id = old.enterprise_id
    label = new_label or old.label
    old_idp_id = old.idp_id
    old_scope = old.scope

    old.is_active = False
    old.updated_at = datetime.now(UTC)

    raw, new_token = await create_scim_token(
        enterprise_id=enterprise_id,
        label=label,
        ttl_days=ttl_days,
        actor_id=actor_id,
        session=session,
        idp_id=old_idp_id,
        scope=old_scope,
    )
    # Override the create audit with a rotation-specific event
    await _audit(
        session,
        "scim.token.rotated",
        actor_id,
        new_token.id,
        f"SCIM token rotated — old={token_id} new={new_token.id}",
        {
            "enterprise_id": enterprise_id,
            "old_token_id": token_id,
            "new_token_id": new_token.id,
            "idp_id": old_idp_id,
            "scope": old_scope,
        },
    )
    return raw, new_token


async def verify_scim_token(
    raw_token: str,
    session: AsyncSession,
) -> SCIMTokenModel | None:
    """Return the SCIMTokenModel if valid, active, and unexpired.

    Updates last_used_at and use_count.
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
    idp_id: str | None = None,
) -> list[SCIMTokenModel]:
    stmt = (
        select(SCIMTokenModel)
        .where(SCIMTokenModel.enterprise_id == enterprise_id)
        .order_by(SCIMTokenModel.created_at.desc())
    )
    if idp_id is not None:
        stmt = stmt.where(SCIMTokenModel.idp_id == idp_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_scim_usage(
    enterprise_id: str,
    session: AsyncSession,
) -> dict:
    """Return per-enterprise SCIM token usage summary for the dashboard."""
    all_tokens = await list_scim_tokens(enterprise_id, session)
    active = [t for t in all_tokens if t.is_active]
    now = datetime.now(UTC)
    not_expired = [
        t for t in active
        if t.expires_at is None or t.expires_at > now
    ]

    last_provisioning = None
    last_sync = None
    for t in all_tokens:
        if t.last_used_at:
            if last_provisioning is None or t.last_used_at > last_provisioning:
                last_provisioning = t.last_used_at
            if last_sync is None or t.last_used_at > last_sync:
                last_sync = t.last_used_at

    # Per-idp breakdown
    per_idp: dict[str, dict] = {}
    for t in all_tokens:
        key = t.idp_id or "__enterprise__"
        entry = per_idp.setdefault(key, {
            "idp_id": t.idp_id,
            "token_count": 0,
            "active_count": 0,
            "last_used_at": None,
        })
        entry["token_count"] += 1
        if t.is_active:
            entry["active_count"] += 1
        if t.last_used_at:
            if entry["last_used_at"] is None or t.last_used_at > entry["last_used_at"]:
                entry["last_used_at"] = t.last_used_at

    return {
        "enterprise_id": enterprise_id,
        "token_count": len(all_tokens),
        "active_tokens": len(not_expired),
        "last_provisioning": last_provisioning,
        "last_sync": last_sync,
        "per_idp_usage": list(per_idp.values()),
    }
