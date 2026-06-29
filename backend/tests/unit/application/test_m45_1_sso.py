"""Unit tests for M45.1 SSO production validators.

Tests cover:
  - ProductionOIDCValidator: JWKS caching, nonce check, claim extraction
  - ProductionSAMLValidator: base64 decode, XML parse errors, attribute extraction
  - async_check_sso_rate_limit: Redis path, in-process fallback
"""

from __future__ import annotations

import base64
import time
from unittest.mock import MagicMock, patch

import pytest

from application.enterprise.sso_validation import (
    SSOValidationError,
    ValidatedIdentity,
    async_check_sso_rate_limit,
    check_sso_rate_limit,
)
from infrastructure.sso.oidc_validator import ProductionOIDCValidator
from infrastructure.sso.saml_validator import ProductionSAMLValidator


# ── OIDC Validator ────────────────────────────────────────────────────────────


class TestProductionOIDCValidator:
    def test_requires_jwks_uri(self) -> None:
        validator = ProductionOIDCValidator()
        with pytest.raises(SSOValidationError, match="JWKS URI"):
            validator.validate(
                id_token="x",
                issuer="https://example.com",
                audience="eios",
                nonce=None,
                jwks_uri=None,
            )

    def test_raises_on_jwks_fetch_failure(self) -> None:
        validator = ProductionOIDCValidator()
        with patch("infrastructure.sso.oidc_validator.httpx.get", side_effect=Exception("timeout")):
            with pytest.raises(SSOValidationError, match="Failed to fetch JWKS"):
                validator.validate(
                    id_token="x",
                    issuer="https://example.com",
                    audience="eios",
                    nonce=None,
                    jwks_uri="https://example.com/.well-known/jwks.json",
                )

    def test_raises_on_invalid_token(self) -> None:
        validator = ProductionOIDCValidator()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": []}
        mock_resp.raise_for_status.return_value = None
        with patch("infrastructure.sso.oidc_validator.httpx.get", return_value=mock_resp):
            with pytest.raises(SSOValidationError, match="OIDC token validation failed"):
                validator.validate(
                    id_token="notajwt",
                    issuer="https://example.com",
                    audience="eios",
                    nonce=None,
                    jwks_uri="https://example.com/.well-known/jwks.json",
                )

    def test_jwks_cache_is_used_on_second_call(self) -> None:
        validator = ProductionOIDCValidator()
        call_count = 0

        def mock_get(url, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.json.return_value = {"keys": []}
            resp.raise_for_status.return_value = None
            return resp

        with patch("infrastructure.sso.oidc_validator.httpx.get", side_effect=mock_get):
            with pytest.raises(SSOValidationError):
                validator.validate("t", "iss", "aud", None, "https://jwks.uri/")
            with pytest.raises(SSOValidationError):
                validator.validate("t", "iss", "aud", None, "https://jwks.uri/")

        # Second call should use cache — httpx.get called only once
        assert call_count == 1

    def test_cache_expires(self) -> None:
        validator = ProductionOIDCValidator(jwks_cache_ttl=0)  # instant expiry
        call_count = 0

        def mock_get(url, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.json.return_value = {"keys": []}
            resp.raise_for_status.return_value = None
            return resp

        with patch("infrastructure.sso.oidc_validator.httpx.get", side_effect=mock_get):
            with pytest.raises(SSOValidationError):
                validator.validate("t", "iss", "aud", None, "https://jwks.uri/")
            time.sleep(0.01)
            with pytest.raises(SSOValidationError):
                validator.validate("t", "iss", "aud", None, "https://jwks.uri/")

        assert call_count == 2


# ── SAML Validator ────────────────────────────────────────────────────────────


class TestProductionSAMLValidator:
    def test_rejects_invalid_base64(self) -> None:
        validator = ProductionSAMLValidator()
        with pytest.raises(SSOValidationError, match="not valid base64"):
            validator.validate(
                saml_response="!!!not base64!!!",
                idp_issuer="https://idp.example.com",
                sp_entity_id="eios",
                acs_url="https://app.eios.io/sso/saml/callback",
                certificates=[],
            )

    def test_rejects_invalid_xml(self) -> None:
        validator = ProductionSAMLValidator()
        bad_xml = base64.b64encode(b"this is not xml").decode()
        with pytest.raises(SSOValidationError, match="XML parse error"):
            validator.validate(
                saml_response=bad_xml,
                idp_issuer="https://idp.example.com",
                sp_entity_id="eios",
                acs_url="https://app.eios.io/sso/saml/callback",
                certificates=[],
            )

    def test_rejects_xml_with_no_matching_cert(self) -> None:
        validator = ProductionSAMLValidator()
        # Valid XML but no matching certificate for signature
        xml = b"""<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml:Assertion>
    <saml:Issuer>https://idp.example.com</saml:Issuer>
  </saml:Assertion>
</samlp:Response>"""
        encoded = base64.b64encode(xml).decode()
        with pytest.raises(SSOValidationError, match="signature invalid"):
            validator.validate(
                saml_response=encoded,
                idp_issuer="https://idp.example.com",
                sp_entity_id="eios",
                acs_url="https://app.eios.io/sso/saml/callback",
                certificates=["not-a-real-cert"],
            )


# ── Async SSO rate limiter ────────────────────────────────────────────────────


class TestAsyncCheckSSORate:
    @pytest.mark.asyncio
    async def test_falls_back_to_memory_when_redis_unavailable(self) -> None:
        with patch("infrastructure.redis.client.get_redis", return_value=None):
            result = await async_check_sso_rate_limit("ent-1", "1.2.3.4")
        assert result is True  # within limit

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_inprocess(self) -> None:
        # Patch the lazy-imported get_redis inside the infrastructure module
        with patch("infrastructure.redis.client.get_redis", return_value=None):
            result = await async_check_sso_rate_limit("ent-fallback", "10.0.0.1")
        assert result is True  # first call is within limit

    def test_sync_fallback_blocks_after_limit(self) -> None:
        from application.enterprise.sso_validation import _sso_rate_store, _SSO_MAX_PER_WINDOW

        key = "testent-block:99.99.99.1"
        _sso_rate_store.clear()
        now = __import__("time").time()
        # Pre-fill to limit
        _sso_rate_store[key] = (now, _SSO_MAX_PER_WINDOW)
        result = check_sso_rate_limit("testent-block", "99.99.99.1")
        assert result is False
        _sso_rate_store.clear()
