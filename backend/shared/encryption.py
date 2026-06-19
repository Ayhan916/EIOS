"""
Application-layer field encryption for sensitive values stored in the database.

Usage: webhook subscription secrets.

Encrypted values are stored with a prefix to allow transparent migration:
  - Plaintext:  "raw_secret_value"
  - Encrypted:  "enc:v1:<fernet_token>"

If WEBHOOK_SECRET_KEY is unset, values are stored in plaintext.
Existing plaintext values are returned as-is even after encryption is enabled.
"""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken

from shared.config import settings

_ENC_PREFIX = "enc:v1:"


def _fernet() -> Fernet | None:
    key = settings.webhook_secret_key
    if not key:
        return None
    return Fernet(key.encode())


def encrypt_field(plaintext: str) -> str:
    """Encrypt a field value if WEBHOOK_SECRET_KEY is configured, else return as-is."""
    f = _fernet()
    if f is None:
        return plaintext
    token = f.encrypt(plaintext.encode()).decode()
    return f"{_ENC_PREFIX}{token}"


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a field value, or return as-is if it is plaintext (no prefix)."""
    if not ciphertext.startswith(_ENC_PREFIX):
        return ciphertext  # legacy plaintext — return unchanged
    token = ciphertext[len(_ENC_PREFIX):]
    f = _fernet()
    if f is None:
        raise ValueError(
            "WEBHOOK_SECRET_KEY is not configured but an encrypted secret was found. "
            "Set WEBHOOK_SECRET_KEY to decrypt existing secrets."
        )
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt field: invalid token or wrong key") from exc


def is_encrypted(value: str) -> bool:
    return value.startswith(_ENC_PREFIX)
