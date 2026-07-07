"""
M45 MFA Service — TOTP setup, verification, backup codes, and disable.

Security invariants:
- mfa_secret is Fernet-encrypted before storing in DB; raw secret never persisted
- Backup codes are BCrypt-hashed; plaintext only returned once at setup time
- mfa_enabled remains False until the user completes POST /auth/mfa/confirm
- TOTP verification uses valid_window=1 (±30s clock tolerance)
- Backup codes are single-use; used_at is set atomically on consumption
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import bcrypt
import pyotp
import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings

logger = structlog.get_logger(__name__)

_BACKUP_CODE_COUNT = 10
_BACKUP_CODE_BYTES = 5  # 10 hex chars per code


def _get_fernet() -> Fernet:
    """Return a Fernet instance keyed from WEBHOOK_SECRET_KEY or SECRET_KEY."""
    key_source = settings.webhook_secret_key or settings.secret_key
    # Fernet requires exactly 32 url-safe base64-encoded bytes.
    # Derive a stable 32-byte key from the configured secret via truncation/padding.
    import base64
    import hashlib

    raw = hashlib.sha256(key_source.encode()).digest()  # always 32 bytes
    fernet_key = base64.urlsafe_b64encode(raw)
    return Fernet(fernet_key)


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("MFA secret decryption failed — key may have changed") from exc


def _hash_backup_code(code: str) -> str:
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()


def _verify_backup_code(code: str, code_hash: str) -> bool:
    return bcrypt.checkpw(code.encode(), code_hash.encode())


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_otp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="EIOS",
    )


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


@dataclass
class MFASetupResult:
    otp_uri: str
    backup_codes: list[str]


async def setup_mfa(user_id: str, email: str, session: AsyncSession) -> MFASetupResult:
    """Generate a new TOTP secret + backup codes. Does NOT enable MFA yet."""
    raw_secret = generate_totp_secret()
    encrypted = encrypt_secret(raw_secret)
    otp_uri = build_otp_uri(raw_secret, email)

    # Generate backup codes
    plaintext_codes = [
        secrets.token_hex(_BACKUP_CODE_BYTES).upper() for _ in range(_BACKUP_CODE_COUNT)
    ]

    # Persist encrypted secret (mfa_enabled stays False until confirm)
    await session.execute(
        text(
            "UPDATE users SET encrypted_mfa_secret = :secret, mfa_enabled = FALSE "
            "WHERE id = :user_id"
        ),
        {"secret": encrypted, "user_id": user_id},
    )

    # Delete any old backup codes first, then insert new ones
    await session.execute(
        text("DELETE FROM mfa_backup_codes WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    now = datetime.now(UTC)
    for code in plaintext_codes:
        await session.execute(
            text(
                "INSERT INTO mfa_backup_codes (id, user_id, code_hash, created_at) "
                "VALUES (:id, :user_id, :code_hash, :created_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "code_hash": _hash_backup_code(code),
                "created_at": now,
            },
        )

    logger.info("mfa_setup_initiated", user_id=user_id)
    return MFASetupResult(otp_uri=otp_uri, backup_codes=plaintext_codes)


async def confirm_mfa(user_id: str, code: str, session: AsyncSession) -> bool:
    """Verify the TOTP code and activate MFA for the user. Returns False on bad code."""
    row = await session.execute(
        text("SELECT encrypted_mfa_secret FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    result = row.fetchone()
    if result is None or result[0] is None:
        return False

    raw_secret = decrypt_secret(result[0])
    if not verify_totp(raw_secret, code):
        return False

    await session.execute(
        text("UPDATE users SET mfa_enabled = TRUE, mfa_confirmed_at = :now WHERE id = :user_id"),
        {"now": datetime.now(UTC), "user_id": user_id},
    )
    logger.info("mfa_confirmed", user_id=user_id)
    return True


async def verify_mfa_code(user_id: str, code: str, session: AsyncSession) -> bool:
    """Verify a TOTP code for login. Returns True on success."""
    row = await session.execute(
        text("SELECT encrypted_mfa_secret, mfa_enabled FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    result = row.fetchone()
    if result is None or not result[1] or result[0] is None:
        return False

    raw_secret = decrypt_secret(result[0])
    verified = verify_totp(raw_secret, code)
    if verified:
        logger.info("mfa_verified", user_id=user_id)
    else:
        logger.warning("mfa_verification_failed", user_id=user_id)
    return verified


async def consume_backup_code(user_id: str, code: str, session: AsyncSession) -> bool:
    """Use a backup code to disable MFA or verify identity. Single-use."""
    rows = await session.execute(
        text(
            "SELECT id, code_hash FROM mfa_backup_codes "
            "WHERE user_id = :user_id AND used_at IS NULL"
        ),
        {"user_id": user_id},
    )
    candidates = rows.fetchall()

    for row_id, code_hash in candidates:
        if _verify_backup_code(code, code_hash):
            await session.execute(
                text("UPDATE mfa_backup_codes SET used_at = :now WHERE id = :id"),
                {"now": datetime.now(UTC), "id": row_id},
            )
            logger.info("mfa_backup_code_consumed", user_id=user_id)
            return True
    return False


async def disable_mfa(user_id: str, backup_code: str, session: AsyncSession) -> bool:
    """Disable MFA using a backup code. Returns False if code is invalid."""
    if not await consume_backup_code(user_id, backup_code, session):
        return False

    await session.execute(
        text(
            "UPDATE users SET mfa_enabled = FALSE, encrypted_mfa_secret = NULL, "
            "mfa_confirmed_at = NULL WHERE id = :user_id"
        ),
        {"user_id": user_id},
    )
    await session.execute(
        text("DELETE FROM mfa_backup_codes WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    logger.info("mfa_disabled", user_id=user_id)
    return True
