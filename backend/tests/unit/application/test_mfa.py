"""Unit tests for M45 MFA service.

Tests run without a real database or Redis — they test the pure logic:
  - TOTP secret generation + URI building
  - TOTP verification (valid / invalid / window)
  - Backup code hashing + verification
  - Fernet encryption/decryption of MFA secrets
"""

from __future__ import annotations

import pyotp
import pytest

from application.mfa.service import (
    _hash_backup_code,
    _verify_backup_code,
    build_otp_uri,
    decrypt_secret,
    encrypt_secret,
    generate_totp_secret,
    verify_totp,
)


class TestTOTPSecretGeneration:
    def test_generates_valid_base32_secret(self) -> None:
        secret = generate_totp_secret()
        assert len(secret) >= 16
        # pyotp base32 secrets are uppercase letters + digits
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in secret)

    def test_generates_unique_secrets(self) -> None:
        secrets = {generate_totp_secret() for _ in range(10)}
        assert len(secrets) == 10


class TestTOTPVerification:
    def test_valid_code_accepted(self) -> None:
        secret = generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert verify_totp(secret, code) is True

    def test_invalid_code_rejected(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False

    def test_wrong_secret_rejected(self) -> None:
        secret_a = generate_totp_secret()
        secret_b = generate_totp_secret()
        code = pyotp.TOTP(secret_a).now()
        assert verify_totp(secret_b, code) is False

    def test_empty_code_rejected(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "") is False


class TestOTPUri:
    def test_uri_contains_issuer(self) -> None:
        uri = build_otp_uri("JBSWY3DPEHPK3PXP", "user@example.com")
        assert "EIOS" in uri

    def test_uri_contains_email(self) -> None:
        uri = build_otp_uri("JBSWY3DPEHPK3PXP", "user@example.com")
        assert "user%40example.com" in uri or "user@example.com" in uri

    def test_uri_starts_with_otpauth(self) -> None:
        uri = build_otp_uri("JBSWY3DPEHPK3PXP", "user@example.com")
        assert uri.startswith("otpauth://totp/")


class TestMFASecretEncryption:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        plaintext = generate_totp_secret()
        ciphertext = encrypt_secret(plaintext)
        assert ciphertext != plaintext
        recovered = decrypt_secret(ciphertext)
        assert recovered == plaintext

    def test_ciphertext_differs_per_call(self) -> None:
        secret = generate_totp_secret()
        c1 = encrypt_secret(secret)
        c2 = encrypt_secret(secret)
        # Fernet uses random IV — same input produces different ciphertext
        assert c1 != c2

    def test_decrypt_wrong_value_raises(self) -> None:
        with pytest.raises(ValueError, match="decryption failed"):
            decrypt_secret("not-valid-fernet-token")


class TestBackupCodes:
    def test_hash_and_verify(self) -> None:
        code = "ABCDE12345"
        code_hash = _hash_backup_code(code)
        assert _verify_backup_code(code, code_hash) is True

    def test_wrong_code_fails(self) -> None:
        code_hash = _hash_backup_code("ABCDE12345")
        assert _verify_backup_code("WRONG00000", code_hash) is False

    def test_case_sensitive(self) -> None:
        code_hash = _hash_backup_code("ABCDE12345")
        assert _verify_backup_code("abcde12345", code_hash) is False
