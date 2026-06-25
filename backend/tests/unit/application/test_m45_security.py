"""Unit tests for M45 JWT hardening.

Tests:
  - jti is present in all token payloads
  - Access token TTL is 15 minutes
  - Refresh token has rotation-compatible jti
  - MFA session token has correct type
  - Blacklist functions handle None Redis gracefully
"""

from __future__ import annotations

import pytest
import jwt as pyjwt

from shared.security import (
    create_access_token,
    create_refresh_token,
    create_mfa_session_token,
    decode_token,
    ALGORITHM,
)
from shared.config import settings


class TestJWTPayloads:
    def test_access_token_has_jti(self) -> None:
        token = create_access_token("user-1", "a@b.com", "analyst")
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) == 36  # UUID4

    def test_refresh_token_has_jti(self) -> None:
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert "jti" in payload

    def test_mfa_session_token_type(self) -> None:
        token = create_mfa_session_token("user-1")
        payload = decode_token(token)
        assert payload["type"] == "mfa_challenge"
        assert "jti" in payload

    def test_access_token_ttl_is_15_minutes(self) -> None:
        token = create_access_token("user-1", "a@b.com", "analyst")
        payload = decode_token(token)
        ttl_seconds = payload["exp"] - payload["iat"]
        assert ttl_seconds == settings.access_token_expire_minutes * 60

    def test_access_tokens_have_unique_jti(self) -> None:
        tokens = [create_access_token("u", "e@e.com", "viewer") for _ in range(5)]
        jtis = [decode_token(t)["jti"] for t in tokens]
        assert len(set(jtis)) == 5

    def test_access_token_type_is_access(self) -> None:
        token = create_access_token("user-1", "a@b.com", "analyst")
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self) -> None:
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert payload["type"] == "refresh"


class TestBlacklistWithoutRedis:
    """Without a real Redis, blacklist functions should degrade gracefully."""

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_returns_false_without_redis(self) -> None:
        from shared.security import is_token_blacklisted
        # Redis is not initialised in unit tests
        result = await is_token_blacklisted("some-jti")
        assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_token_does_not_raise_without_redis(self) -> None:
        from shared.security import blacklist_token
        # Should silently succeed (no Redis available)
        await blacklist_token("some-jti", ttl_seconds=900)
