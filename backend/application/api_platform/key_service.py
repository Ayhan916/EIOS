"""
API Key generation and validation utilities.

Keys use the format:  eios_<40 lowercase hex chars>
Hash storage:         SHA-256 hex digest of the raw key
Key prefix (display): first 12 chars of the raw key  →  eios_XXXXXXX
"""

from __future__ import annotations

import hashlib
import secrets

_KEY_PREFIX = "eios_"
_RAW_BYTES = 20  # → 40 hex chars → total key length = 45


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_prefix).

    Only ``raw_key`` is returned to the caller at creation time;
    only ``key_hash`` and ``key_prefix`` are stored in the database.
    """
    raw = _KEY_PREFIX + secrets.token_hex(_RAW_BYTES)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:12]
    return raw, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest for a raw key (for lookup)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def is_api_key_token(token: str) -> bool:
    """Return True if the token is an EIOS API key (not a JWT)."""
    return token.startswith(_KEY_PREFIX)
