"""
EIOS Security Utilities

Password hashing (bcrypt), JWT encode/decode, and token blacklist (Redis).
All cryptographic operations are centralised here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from shared.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_mfa_session_token(user_id: str) -> str:
    """Short-lived token issued after password check when MFA is enabled.
    Must be presented to POST /auth/mfa/verify to complete login.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "mfa_challenge",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.mfa_session_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:  # type: ignore[type-arg]
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


# ── JWT Blacklist (Redis-backed) ──────────────────────────────────────────────


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token's jti to the dedicated noeviction blacklist Redis.

    Uses the blacklist client (noeviction) so revoked tokens are never silently
    dropped due to memory pressure.  Falls back silently if Redis is unavailable.
    """
    from infrastructure.redis.blacklist import get_redis_blacklist
    redis = get_redis_blacklist()
    if redis is not None:
        await redis.setex(f"blacklist:{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if this token's jti has been revoked.

    Returns False when the blacklist Redis is unavailable — fail-open is
    acceptable here because tokens still expire naturally via 'exp'.
    """
    from infrastructure.redis.blacklist import get_redis_blacklist
    redis = get_redis_blacklist()
    if redis is None:
        return False
    result = await redis.get(f"blacklist:{jti}")
    return result is not None


# ── M35 Supplier Portal JWT ───────────────────────────────────────────────────

_SUPPLIER_AUDIENCE = "eios-supplier"
_INTERNAL_AUDIENCE = "eios-internal"


def create_supplier_access_token(
    supplier_user_id: str,
    email: str,
    role: str,
    supplier_id: str,
) -> str:
    """Create a JWT with aud=eios-supplier.  Rejected by internal auth."""
    now = datetime.now(UTC)
    payload = {
        "sub": supplier_user_id,
        "email": email,
        "role": role,
        "supplier_id": supplier_id,
        "aud": _SUPPLIER_AUDIENCE,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_supplier_refresh_token(supplier_user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": supplier_user_id,
        "aud": _SUPPLIER_AUDIENCE,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_supplier_token(token: str) -> dict:  # type: ignore[type-arg]
    """Decode a supplier JWT.  Raises if audience is not eios-supplier."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        audience=_SUPPLIER_AUDIENCE,
        options={"verify_aud": True},
    )


# ── M45.1 External Auditor Access Tokens ────────────────────────────────────

_EXTERNAL_AUDIT_AUDIENCE = "eios-external-audit"


def create_external_audit_token(
    token_id: str,
    org_id: str,
    label: str,
    issued_by: str,
) -> str:
    """72h scoped read-only JWT for external auditors.

    No refresh token is issued.  Revocable via Redis blacklist using token_id
    (which doubles as the jti).  Audience is eios-external-audit so decode_token()
    correctly rejects it — use decode_external_audit_token() to verify.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": token_id,
        "aud": _EXTERNAL_AUDIT_AUDIENCE,
        "type": "access",
        "role": "external_auditor",
        "org_id": org_id,
        "label": label,
        "issued_by": issued_by,
        "jti": token_id,  # token_id == jti — simplifies revocation
        "iat": now,
        "exp": now + timedelta(hours=settings.external_audit_token_expire_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_external_audit_token(token: str) -> dict:  # type: ignore[type-arg]
    """Decode an external audit JWT.  Raises if audience is not eios-external-audit."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        audience=_EXTERNAL_AUDIT_AUDIENCE,
        options={"verify_aud": True},
    )


def create_invitation_token(email: str, supplier_id: str, role: str) -> str:
    """Short-lived token embedded in supplier invite emails."""
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "supplier_id": supplier_id,
        "role": role,
        "aud": _SUPPLIER_AUDIENCE,
        "type": "invitation",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=72),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
