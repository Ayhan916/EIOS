"""SSO trust layer — M40.3.

Defines ValidatedIdentity: the only accepted input to process_sso_login().

SAML and OIDC validators are expressed as Protocols so production code
can swap in real validation libraries (python-saml, python-jose) without
changing callers.  Tests inject mock validators that return pre-built
ValidatedIdentity objects or raise SSOValidationError.

Flow:
  1.  IdP posts assertion/token to SAML or OIDC callback endpoint.
  2.  Endpoint loads the IdentityProviderModel to get issuer + config.
  3.  Endpoint calls SAMLValidator.validate() or OIDCValidator.validate().
  4.  On success, receives a ValidatedIdentity — groups are extracted from
      the assertion/token, never from caller-supplied request body fields.
  5.  Endpoint calls process_sso_login(enterprise_id, validated_identity, session).
  6.  process_sso_login() applies group mappings and writes audit events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SSOValidationError(Exception):
    """Raised when an SSO assertion or token fails validation."""

    def __init__(self, reason: str, idp_id: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.idp_id = idp_id


@dataclass
class ValidatedIdentity:
    """A cryptographically-verified identity from an SSO provider.

    Only constructed by SAMLValidator or OIDCValidator after successful
    signature/token verification.  Never constructed from raw client claims.
    """

    external_id: str          # subject NameID (SAML) or sub (OIDC)
    email: str
    groups: list[str]         # group claims extracted from assertion/token
    issuer: str               # IdP issuer URI — must match IdentityProviderModel.issuer
    idp_id: str               # internal IdentityProviderModel.id
    display_name: str | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)


class SAMLAssertionValidator(Protocol):
    """Adapter interface for SAML 2.0 assertion validation.

    Implementations should use a SAML library (e.g. python-saml, onelogin).
    No saml library is imported here — this is the adapter boundary.
    """

    def validate(
        self,
        saml_response: str,
        idp_issuer: str,
        sp_entity_id: str,
        acs_url: str,
        certificates: list[str],
        group_attribute: str = "groups",
    ) -> ValidatedIdentity:
        """Parse and verify a base64-encoded SAMLResponse.

        Must verify:
          - Signature against idp certificates
          - Issuer matches idp_issuer
          - Audience / sp_entity_id
          - NotBefore / NotOnOrAfter conditions

        Returns ValidatedIdentity with groups extracted from the named attribute.
        Raises SSOValidationError on any failure.
        """
        ...


class OIDCTokenValidator(Protocol):
    """Adapter interface for OIDC ID token validation.

    Implementations should use a JWT library (e.g. python-jose, PyJWT).
    No jwt library is imported here — this is the adapter boundary.
    """

    def validate(
        self,
        id_token: str,
        issuer: str,
        audience: str,
        nonce: str | None,
        jwks_uri: str | None = None,
        group_claim: str = "groups",
    ) -> ValidatedIdentity:
        """Validate an OIDC ID token.

        Must verify:
          - Signature (via JWKS or certificates)
          - iss == issuer
          - aud contains audience
          - nonce (if provided) matches token nonce claim
          - exp / nbf / iat

        Returns ValidatedIdentity with groups extracted from group_claim.
        Raises SSOValidationError on any failure.
        """
        ...


class MockSAMLValidator:
    """Test double for SAMLAssertionValidator.

    Inject a pre-built ValidatedIdentity to return, or an exception to raise.
    """

    def __init__(
        self,
        result: ValidatedIdentity | None = None,
        error: SSOValidationError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.call_count = 0
        self.last_call: dict[str, Any] = {}

    def validate(
        self,
        saml_response: str,
        idp_issuer: str,
        sp_entity_id: str,
        acs_url: str,
        certificates: list[str],
        group_attribute: str = "groups",
    ) -> ValidatedIdentity:
        self.call_count += 1
        self.last_call = {
            "saml_response": saml_response,
            "idp_issuer": idp_issuer,
            "sp_entity_id": sp_entity_id,
            "acs_url": acs_url,
        }
        if self._error:
            raise self._error
        if self._result is None:
            raise SSOValidationError("MockSAMLValidator: no result configured")
        return self._result


class MockOIDCValidator:
    """Test double for OIDCTokenValidator."""

    def __init__(
        self,
        result: ValidatedIdentity | None = None,
        error: SSOValidationError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.call_count = 0
        self.last_call: dict[str, Any] = {}

    def validate(
        self,
        id_token: str,
        issuer: str,
        audience: str,
        nonce: str | None,
        jwks_uri: str | None = None,
        group_claim: str = "groups",
    ) -> ValidatedIdentity:
        self.call_count += 1
        self.last_call = {
            "id_token": id_token,
            "issuer": issuer,
            "audience": audience,
            "nonce": nonce,
        }
        if self._error:
            raise self._error
        if self._result is None:
            raise SSOValidationError("MockOIDCValidator: no result configured")
        return self._result


# ── Simple in-process rate limiter for SSO callbacks ─────────────────────────
#
# Keyed by (enterprise_id, remote_ip).  In production replace with Redis.
# Stored as {key: (window_start_unix, count)}.

import time as _time
from threading import Lock as _Lock

_sso_rate_store: dict[str, tuple[float, int]] = {}
_sso_rate_lock = _Lock()

_SSO_WINDOW_SECONDS = 60
_SSO_MAX_PER_WINDOW = 20


def check_sso_rate_limit(enterprise_id: str, remote_ip: str) -> bool:
    """Return True if the request is within rate limits, False if it should be rejected."""
    key = f"{enterprise_id}:{remote_ip}"
    now = _time.time()
    with _sso_rate_lock:
        entry = _sso_rate_store.get(key)
        if entry is None or (now - entry[0]) >= _SSO_WINDOW_SECONDS:
            _sso_rate_store[key] = (now, 1)
            return True
        window_start, count = entry
        if count >= _SSO_MAX_PER_WINDOW:
            return False
        _sso_rate_store[key] = (window_start, count + 1)
        return True
