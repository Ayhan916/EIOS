"""Production OIDC ID token validator (M45.1 — G-002).

Uses python-jose for JWT verification and httpx for synchronous JWKS fetching.
JWKS keys are cached in memory (TTL=1h) to avoid per-request HTTP calls.

Implements the OIDCTokenValidator Protocol from application.enterprise.sso_validation.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from jose import JWTError
from jose import jwt as jose_jwt

from application.enterprise.sso_validation import SSOValidationError, ValidatedIdentity

_OIDC_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
_JWKS_CACHE_TTL = 3600  # seconds


class ProductionOIDCValidator:
    """OIDC ID token validator backed by python-jose and live JWKS fetching."""

    def __init__(self, jwks_cache_ttl: int = _JWKS_CACHE_TTL) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = threading.Lock()
        self._cache_ttl = jwks_cache_ttl

    def _get_jwks(self, jwks_uri: str) -> list[dict[str, Any]]:
        now = time.monotonic()
        with self._lock:
            if jwks_uri in self._cache:
                ts, keys = self._cache[jwks_uri]
                if now - ts < self._cache_ttl:
                    return keys

        try:
            resp = httpx.get(jwks_uri, timeout=5, follow_redirects=True)
            resp.raise_for_status()
            keys = resp.json().get("keys", [])
        except Exception as exc:
            raise SSOValidationError(f"Failed to fetch JWKS from {jwks_uri}: {exc}") from exc

        with self._lock:
            self._cache[jwks_uri] = (now, keys)
        return keys

    def validate(
        self,
        id_token: str,
        issuer: str,
        audience: str,
        nonce: str | None,
        jwks_uri: str | None = None,
        group_claim: str = "groups",
    ) -> ValidatedIdentity:
        if not jwks_uri:
            raise SSOValidationError("OIDC validation requires a JWKS URI")

        keys = self._get_jwks(jwks_uri)

        try:
            claims: dict[str, Any] = jose_jwt.decode(
                id_token,
                keys,
                algorithms=_OIDC_ALGORITHMS,
                audience=audience,
                issuer=issuer,
                options={"verify_at_hash": False},
            )
        except JWTError as exc:
            raise SSOValidationError(f"OIDC token validation failed: {exc}") from exc

        if nonce is not None and claims.get("nonce") != nonce:
            raise SSOValidationError("OIDC nonce mismatch")

        sub = claims.get("sub")
        if not sub:
            raise SSOValidationError("OIDC token missing required 'sub' claim")

        email: str = (
            claims.get("email")
            or claims.get("preferred_username")
            or sub
        )
        display_name: str | None = claims.get("name")
        raw_groups = claims.get(group_claim, [])
        groups: list[str] = [raw_groups] if isinstance(raw_groups, str) else list(raw_groups)

        return ValidatedIdentity(
            external_id=sub,
            email=email,
            groups=groups,
            issuer=issuer,
            idp_id="",  # caller sets this after validation
            display_name=display_name,
            raw_claims=dict(claims),
        )
