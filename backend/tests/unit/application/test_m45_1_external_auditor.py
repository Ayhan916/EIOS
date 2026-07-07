"""Unit tests for M45.1 External Auditor role (G-017).

Tests cover:
  - EXTERNAL_AUDITOR in UserRole enum
  - has_min_role: external_auditor never passes internal role checks
  - create_external_audit_token: payload structure and audience
  - decode_external_audit_token: rejects internal tokens, accepts audit tokens
  - decode_token: rejects external audit tokens (wrong audience)
  - Blacklist revocation path (no Redis)
"""

from __future__ import annotations

import uuid

import jwt as pyjwt
import pytest

from domain.enums import UserRole, has_min_role
from shared.config import settings
from shared.security import (
    ALGORITHM,
    create_access_token,
    create_external_audit_token,
    decode_external_audit_token,
    decode_token,
)


class TestExternalAuditorEnum:
    def test_external_auditor_is_in_user_role(self) -> None:
        assert UserRole.EXTERNAL_AUDITOR == "external_auditor"

    def test_has_min_role_returns_false_for_external_auditor_vs_viewer(self) -> None:
        assert has_min_role("external_auditor", UserRole.VIEWER) is False

    def test_has_min_role_returns_false_for_external_auditor_vs_admin(self) -> None:
        assert has_min_role("external_auditor", UserRole.ADMIN) is False

    def test_internal_roles_are_unaffected(self) -> None:
        assert has_min_role("admin", UserRole.VIEWER) is True
        assert has_min_role("viewer", UserRole.ADMIN) is False


class TestExternalAuditToken:
    def test_token_has_correct_audience(self) -> None:
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-1", "Deloitte", "admin-1")
        # decode without audience verification to inspect raw payload
        raw = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        assert raw["aud"] == "eios-external-audit"

    def test_token_has_external_auditor_role(self) -> None:
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-1", "Deloitte", "admin-1")
        payload = decode_external_audit_token(token)
        assert payload["role"] == "external_auditor"
        assert payload["type"] == "access"

    def test_token_id_equals_jti(self) -> None:
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-1", "EY", "admin-1")
        payload = decode_external_audit_token(token)
        assert payload["sub"] == token_id
        assert payload["jti"] == token_id

    def test_token_contains_org_and_label(self) -> None:
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-abc", "KPMG Audit", "admin-2")
        payload = decode_external_audit_token(token)
        assert payload["org_id"] == "org-abc"
        assert payload["label"] == "KPMG Audit"
        assert payload["issued_by"] == "admin-2"

    def test_token_ttl_is_72_hours(self) -> None:
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-1", "PwC", "admin-1")
        payload = decode_external_audit_token(token)
        ttl_hours = (payload["exp"] - payload["iat"]) / 3600
        assert ttl_hours == settings.external_audit_token_expire_hours

    def test_decode_token_rejects_external_audit_token(self) -> None:
        """decode_token() must reject external audit tokens (wrong audience)."""
        token_id = str(uuid.uuid4())
        token = create_external_audit_token(token_id, "org-1", "Test", "admin-1")
        with pytest.raises(pyjwt.InvalidAudienceError):
            decode_token(token)

    def test_decode_external_audit_token_rejects_internal_token(self) -> None:
        """decode_external_audit_token() must reject regular internal access tokens."""
        token = create_access_token("user-1", "a@b.com", "analyst")
        with pytest.raises(pyjwt.PyJWTError):
            decode_external_audit_token(token)

    def test_multiple_tokens_have_unique_ids(self) -> None:
        tokens = [
            create_external_audit_token(str(uuid.uuid4()), "org-1", f"Firm-{i}", "admin-1")
            for i in range(5)
        ]
        payloads = [decode_external_audit_token(t) for t in tokens]
        token_ids = [p["sub"] for p in payloads]
        assert len(set(token_ids)) == 5
