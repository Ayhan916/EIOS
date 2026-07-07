"""M48.2 G-034 — Board Portal Share-Link Service.

Creates and validates time-limited, scoped, read-only JWT tokens for
sharing board reports with external stakeholders (e.g., board members).

Security invariants:
  - No refresh token — access expires after expires_at.
  - JWT payload scope: {"report_id", "org_id", "sections", "exp"}.
  - Raw JWT is never persisted — only SHA-256(token) stored for revocation.
  - Revoked tokens return 410 Gone.
  - Token type: "board_access" (distinct from user JWT type).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from shared.config import settings

_ALGORITHM = "HS256"
_TOKEN_TYPE = "board_access"


def _secret() -> str:
    return settings.secret_key


def create_board_token(
    *,
    report_id: str,
    organization_id: str,
    expires_in_hours: int = 168,
    allowed_sections: list[str] | None = None,
) -> tuple[str, datetime]:
    """Create a signed JWT for board portal access.

    Returns:
        (raw_jwt, expires_at) — caller persists hash(jwt) in DB.
    """
    if expires_in_hours < 1 or expires_in_hours > 720:
        raise ValueError("expires_in_hours must be 1–720")

    expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)

    payload = {
        "type": _TOKEN_TYPE,
        "report_id": report_id,
        "org_id": organization_id,
        "sections": allowed_sections or [],
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, _secret(), algorithm=_ALGORITHM)
    return token, expires_at


def decode_board_token(token: str) -> dict[str, Any]:
    """Decode and verify a board access token.

    Raises:
        jwt.ExpiredSignatureError — token expired
        jwt.InvalidTokenError — invalid signature or claims
        ValueError — wrong token type
    """
    payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    if payload.get("type") != _TOKEN_TYPE:
        raise ValueError("Not a board access token")
    return payload


def hash_token(token: str) -> str:
    """Return SHA-256 hex digest of the raw JWT for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def is_section_allowed(payload: dict[str, Any], section: str) -> bool:
    """Return True if the requested section is in the token's allowed sections.

    Empty allowed_sections means all sections are accessible.
    """
    sections = payload.get("sections", [])
    return not sections or section in sections
