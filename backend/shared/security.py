"""
EIOS Security Utilities

Password hashing (bcrypt) and JWT encode/decode.
All cryptographic operations are centralised here.
"""

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
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:  # type: ignore[type-arg]
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


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


def create_invitation_token(email: str, supplier_id: str, role: str) -> str:
    """Short-lived token embedded in supplier invite emails."""
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "supplier_id": supplier_id,
        "role": role,
        "aud": _SUPPLIER_AUDIENCE,
        "type": "invitation",
        "iat": now,
        "exp": now + timedelta(hours=72),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
