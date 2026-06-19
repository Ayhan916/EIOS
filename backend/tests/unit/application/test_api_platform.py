"""
Unit tests for M30 API Platform — key generation and webhook signing.

No I/O, no DB, no network.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from application.api_platform.key_service import (
    generate_api_key,
    hash_api_key,
    is_api_key_token,
)
from application.api_platform.webhook_service import (
    canonical_body,
    next_retry_at,
    payload_hash,
    sign_payload,
)


# ── Key generation ─────────────────────────────────────────────────────────────


class TestGenerateApiKey:
    def test_format(self) -> None:
        raw, _, _ = generate_api_key()
        assert raw.startswith("eios_")
        assert len(raw) == 45  # "eios_" (5) + 40 hex chars

    def test_hash_is_sha256_hex(self) -> None:
        raw, key_hash, _ = generate_api_key()
        assert len(key_hash) == 64
        assert key_hash == hashlib.sha256(raw.encode()).hexdigest()

    def test_prefix_is_first_12_chars(self) -> None:
        raw, _, key_prefix = generate_api_key()
        assert key_prefix == raw[:12]
        assert key_prefix.startswith("eios_")

    def test_uniqueness(self) -> None:
        keys = {generate_api_key()[0] for _ in range(50)}
        assert len(keys) == 50

    def test_hash_api_key_matches_generation(self) -> None:
        raw, key_hash, _ = generate_api_key()
        assert hash_api_key(raw) == key_hash

    def test_hash_is_deterministic(self) -> None:
        raw, _, _ = generate_api_key()
        assert hash_api_key(raw) == hash_api_key(raw)


class TestIsApiKeyToken:
    def test_detects_eios_prefix(self) -> None:
        assert is_api_key_token("eios_abc123") is True

    def test_rejects_jwt(self) -> None:
        assert is_api_key_token("eyJhbGciOiJIUzI1NiJ9.payload.sig") is False

    def test_rejects_empty(self) -> None:
        assert is_api_key_token("") is False

    def test_rejects_partial_prefix(self) -> None:
        assert is_api_key_token("eios") is False

    def test_valid_generated_key(self) -> None:
        raw, _, _ = generate_api_key()
        assert is_api_key_token(raw) is True


# ── Webhook signing ────────────────────────────────────────────────────────────


_PAYLOAD = {"event": "assessment.created", "data": {"id": "abc123"}, "organization_id": "org1"}
_SECRET = "test-secret-minimum-16-chars"


class TestSignPayload:
    def test_returns_sha256_prefix(self) -> None:
        sig = sign_payload(_PAYLOAD, _SECRET)
        assert sig.startswith("sha256=")

    def test_signature_is_hex(self) -> None:
        sig = sign_payload(_PAYLOAD, _SECRET)
        hex_part = sig[len("sha256="):]
        assert len(hex_part) == 64
        int(hex_part, 16)  # raises if not valid hex

    def test_deterministic(self) -> None:
        assert sign_payload(_PAYLOAD, _SECRET) == sign_payload(_PAYLOAD, _SECRET)

    def test_canonical_body_sorted_keys(self) -> None:
        p1 = {"b": 2, "a": 1}
        p2 = {"a": 1, "b": 2}
        assert canonical_body(p1) == canonical_body(p2)

    def test_different_payloads_different_sigs(self) -> None:
        p2 = {**_PAYLOAD, "data": {"id": "different"}}
        assert sign_payload(_PAYLOAD, _SECRET) != sign_payload(p2, _SECRET)

    def test_different_secrets_different_sigs(self) -> None:
        assert sign_payload(_PAYLOAD, _SECRET) != sign_payload(_PAYLOAD, "other-secret-min-16")

    def test_matches_manual_hmac(self) -> None:
        body = json.dumps(_PAYLOAD, separators=(",", ":"), sort_keys=True).encode()
        expected = "sha256=" + hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
        assert sign_payload(_PAYLOAD, _SECRET) == expected

    def test_payload_hash_is_sha256_of_canonical(self) -> None:
        body = canonical_body(_PAYLOAD)
        expected = hashlib.sha256(body).hexdigest()
        assert payload_hash(_PAYLOAD) == expected


# ── Retry schedule ─────────────────────────────────────────────────────────────


class TestNextRetryAt:
    def test_attempt_0_immediate(self) -> None:
        # attempt 0 means first retry after immediate delivery failed
        result = next_retry_at(0)
        assert result is not None

    def test_attempt_1_one_minute(self) -> None:
        from datetime import UTC, datetime, timedelta
        before = datetime.now(UTC)
        result = next_retry_at(1)
        assert result is not None
        delta = (result - before).total_seconds()
        assert 55 <= delta <= 65  # ~1 min with clock jitter tolerance

    def test_attempt_2_five_minutes(self) -> None:
        from datetime import UTC, datetime
        before = datetime.now(UTC)
        result = next_retry_at(2)
        assert result is not None
        delta = (result - before).total_seconds()
        assert 295 <= delta <= 305

    def test_attempt_5_dead_letter(self) -> None:
        assert next_retry_at(5) is None

    def test_attempt_6_dead_letter(self) -> None:
        assert next_retry_at(6) is None

    def test_attempts_0_to_4_return_datetimes(self) -> None:
        for attempt in range(5):
            assert next_retry_at(attempt) is not None
