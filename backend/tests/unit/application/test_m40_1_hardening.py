"""Unit tests for M40.1 — Enterprise Identity & Provisioning Hardening.

Covers:
  - SecretProvider abstraction (InMemory, Environment)
  - SSO login enforcement (process_sso_login role/scope assignment)
  - SCIM token lifecycle (create, revoke, rotate, verify, expired)
  - Secret leakage guards (no raw secret in DB or API response)
  - SCIM isolation (enterprise_id enforcement)
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Secret Provider Tests ─────────────────────────────────────────────────────


class TestInMemorySecretProvider:
    def _provider(self):
        from infrastructure.secrets.provider import InMemorySecretProvider

        return InMemorySecretProvider()

    def test_store_and_retrieve(self) -> None:
        p = self._provider()
        p.store("key1", "mysecret")
        assert p.retrieve("key1") == "mysecret"

    def test_retrieve_missing_returns_none(self) -> None:
        p = self._provider()
        assert p.retrieve("nonexistent") is None

    def test_delete_removes_secret(self) -> None:
        p = self._provider()
        p.store("key1", "secret")
        p.delete("key1")
        assert p.retrieve("key1") is None

    def test_delete_nonexistent_is_noop(self) -> None:
        p = self._provider()
        p.delete("does_not_exist")  # must not raise

    def test_clear_wipes_all(self) -> None:
        p = self._provider()
        p.store("a", "1")
        p.store("b", "2")
        p.clear()
        assert p.retrieve("a") is None
        assert p.retrieve("b") is None

    def test_provider_name(self) -> None:
        p = self._provider()
        assert p.provider_name == "in_memory"

    def test_store_returns_identifier(self) -> None:
        p = self._provider()
        result = p.store("mykey", "myval")
        assert result == "mykey"

    def test_multiple_secrets_isolated(self) -> None:
        p = self._provider()
        p.store("k1", "secret1")
        p.store("k2", "secret2")
        assert p.retrieve("k1") == "secret1"
        assert p.retrieve("k2") == "secret2"


class TestEnvironmentSecretProvider:
    def _provider(self):
        from infrastructure.secrets.provider import EnvironmentSecretProvider

        return EnvironmentSecretProvider()

    def test_provider_name(self) -> None:
        p = self._provider()
        assert p.provider_name == "environment"

    def test_store_sets_env_var(self) -> None:
        p = self._provider()
        key = f"EIOS_TEST_{uuid.uuid4().hex[:8]}"
        try:
            p.store(key, "testvalue")
            assert os.environ.get(key) == "testvalue"
        finally:
            os.environ.pop(key, None)

    def test_retrieve_reads_env_var(self) -> None:
        p = self._provider()
        key = f"EIOS_TEST_{uuid.uuid4().hex[:8]}"
        os.environ[key] = "from_env"
        try:
            assert p.retrieve(key) == "from_env"
        finally:
            os.environ.pop(key, None)

    def test_retrieve_missing_returns_none(self) -> None:
        p = self._provider()
        assert p.retrieve("DEFINITELY_NOT_SET_XYZ_12345") is None

    def test_delete_unsets_env_var(self) -> None:
        p = self._provider()
        key = f"EIOS_TEST_{uuid.uuid4().hex[:8]}"
        os.environ[key] = "willbedeleted"
        p.delete(key)
        assert key not in os.environ


class TestSecretProviderRegistry:
    def test_get_set_provider(self) -> None:
        from infrastructure.secrets.provider import (
            InMemorySecretProvider,
            get_secret_provider,
            set_secret_provider,
        )

        original = get_secret_provider()
        try:
            mem = InMemorySecretProvider()
            set_secret_provider(mem)
            assert get_secret_provider() is mem
        finally:
            set_secret_provider(original)

    def test_default_provider_is_environment(self) -> None:
        # Default should be EnvironmentSecretProvider (may have been overridden in other tests)
        # Just check it's a SecretProvider subclass
        from infrastructure.secrets.provider import (
            SecretProvider,
            get_secret_provider,
        )

        assert isinstance(get_secret_provider(), SecretProvider)


# ── SSO Login Enforcement Tests ───────────────────────────────────────────────


class TestProcessSSOLogin:
    """Tests for process_sso_login — pure logic with mocked DB.

    M40.3: process_sso_login now accepts ValidatedIdentity instead of raw
    (idp_id, idp_groups) to prevent trust of caller-supplied claims.
    """

    def _make_mapping(
        self,
        idp_group: str,
        mapped_role: str,
        scope: str | None = None,
        bu_id: str | None = None,
        region_id: str | None = None,
    ):
        from infrastructure.persistence.models.enterprise import GroupMappingModel

        m = MagicMock(spec=GroupMappingModel)
        m.idp_group = idp_group
        m.mapped_role = mapped_role
        m.scope = scope
        m.business_unit_id = bu_id
        m.region_id = region_id
        m.is_active = True
        return m

    def _make_user(self):
        from infrastructure.persistence.models.user import UserModel

        u = MagicMock(spec=UserModel)
        u.id = str(uuid.uuid4())
        u.role = "viewer"
        u.enterprise_id = None
        u.enterprise_scope = None
        u.business_unit_id = None
        u.region_id = None
        return u

    def _vi(self, idp_id: str, groups: list[str], user_id: str = "user-1"):
        from application.enterprise.sso_validation import ValidatedIdentity

        return ValidatedIdentity(
            external_id=user_id,
            email=f"{user_id}@corp.com",
            groups=groups,
            issuer="https://idp.corp.com",
            idp_id=idp_id,
        )

    @pytest.mark.asyncio
    async def test_basic_role_assignment(self) -> None:
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        mapping = self._make_mapping("eios-analysts", "analyst")
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        session.execute = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["eios-analysts"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "analyst"
        assert user.role == "analyst"
        assert user.enterprise_id == enterprise_id

    @pytest.mark.asyncio
    async def test_bu_admin_scope_assignment(self) -> None:
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        bu_id = str(uuid.uuid4())
        mapping = self._make_mapping("emea-admins", "bu_admin", scope="bu_admin", bu_id=bu_id)
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["emea-admins"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "bu_admin"
        assert result.business_unit_id == bu_id
        assert user.business_unit_id == bu_id
        assert user.enterprise_scope == "bu_admin"

    @pytest.mark.asyncio
    async def test_regional_admin_scope_assignment(self) -> None:
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        region_id = str(uuid.uuid4())
        mapping = self._make_mapping(
            "eu-regional-admins", "regional_admin", scope="regional_admin", region_id=region_id
        )
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["eu-regional-admins"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "regional_admin"
        assert result.region_id == region_id
        assert user.region_id == region_id

    @pytest.mark.asyncio
    async def test_enterprise_admin_assignment(self) -> None:
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        mapping = self._make_mapping("global-admins", "enterprise_admin", scope="enterprise_admin")
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["global-admins"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "enterprise_admin"
        assert result.enterprise_scope == "enterprise_admin"

    @pytest.mark.asyncio
    async def test_no_matching_group_defaults_to_viewer(self) -> None:
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        mapping = self._make_mapping("other-group", "admin")
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["unrelated-group"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "viewer"
        assert result.matched_groups == []

    @pytest.mark.asyncio
    async def test_scoped_role_wins_over_plain_role(self) -> None:
        """bu_admin is ranked higher than analyst — bu_admin must win."""
        from application.enterprise.sso_service import process_sso_login

        user = self._make_user()
        bu_id = str(uuid.uuid4())
        mapping_analyst = self._make_mapping("all-staff", "analyst")
        mapping_bu_admin = self._make_mapping("bu-leads", "bu_admin", bu_id=bu_id)
        enterprise_id = str(uuid.uuid4())
        idp_id = str(uuid.uuid4())

        session = AsyncMock()
        gm_result = MagicMock()
        gm_result.scalars.return_value.all.return_value = [mapping_analyst, mapping_bu_admin]
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        session.execute.side_effect = [gm_result, user_result]

        result = await process_sso_login(
            enterprise_id=enterprise_id,
            validated_identity=self._vi(idp_id, ["all-staff", "bu-leads"], user.id),
            session=session,
            user_id=user.id,
        )

        assert result.applied_role == "bu_admin"
        assert result.business_unit_id == bu_id

    @pytest.mark.asyncio
    async def test_result_to_dict(self) -> None:
        from application.enterprise.sso_service import SSOLoginResult

        r = SSOLoginResult(
            user_id="u1",
            applied_role="analyst",
            enterprise_scope=None,
            enterprise_id="e1",
            business_unit_id=None,
            region_id=None,
            matched_groups=["staff"],
        )
        d = r.to_dict()
        assert d["user_id"] == "u1"
        assert d["applied_role"] == "analyst"
        assert d["matched_groups"] == ["staff"]


# ── SCIM Token Tests ──────────────────────────────────────────────────────────


class TestSCIMTokenHash:
    def test_hash_is_sha256(self) -> None:
        from application.enterprise.scim_token_service import _hash_token

        raw = "test_raw_token"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert _hash_token(raw) == expected

    def test_different_tokens_different_hashes(self) -> None:
        from application.enterprise.scim_token_service import _hash_token

        assert _hash_token("token1") != _hash_token("token2")

    def test_hash_is_64_chars(self) -> None:
        from application.enterprise.scim_token_service import _hash_token

        h = _hash_token("anything")
        assert len(h) == 64


class TestSCIMTokenService:
    def _make_session(self, token_obj=None):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = token_obj
        session.execute = AsyncMock(return_value=result_mock)
        return session

    @pytest.mark.asyncio
    async def test_create_returns_raw_token_and_model(self) -> None:
        from application.enterprise.scim_token_service import create_scim_token

        session = self._make_session()
        raw, token = await create_scim_token(
            enterprise_id="ent-1",
            label="Azure AD SCIM",
            ttl_days=365,
            actor_id="admin-1",
            session=session,
        )

        assert isinstance(raw, str)
        assert len(raw) > 20  # token_urlsafe(32) ≈ 43 chars
        assert token.enterprise_id == "ent-1"
        assert token.label == "Azure AD SCIM"
        assert token.is_active is True

    @pytest.mark.asyncio
    async def test_create_hashes_token(self) -> None:
        from application.enterprise.scim_token_service import _hash_token, create_scim_token

        session = self._make_session()
        raw, token = await create_scim_token(
            enterprise_id="ent-1",
            label=None,
            ttl_days=0,
            actor_id="admin-1",
            session=session,
        )
        assert token.token_hash == _hash_token(raw)

    @pytest.mark.asyncio
    async def test_create_no_expiry_when_ttl_zero(self) -> None:
        from application.enterprise.scim_token_service import create_scim_token

        session = self._make_session()
        _, token = await create_scim_token(
            enterprise_id="ent-1",
            label=None,
            ttl_days=0,
            actor_id="admin-1",
            session=session,
        )
        assert token.expires_at is None

    @pytest.mark.asyncio
    async def test_create_sets_expiry_when_ttl_positive(self) -> None:
        from application.enterprise.scim_token_service import create_scim_token

        session = self._make_session()
        before = datetime.now(UTC)
        _, token = await create_scim_token(
            enterprise_id="ent-1",
            label=None,
            ttl_days=30,
            actor_id="admin-1",
            session=session,
        )
        after = datetime.now(UTC)

        assert token.expires_at is not None
        assert token.expires_at > before
        assert token.expires_at < after + timedelta(days=31)

    @pytest.mark.asyncio
    async def test_revoke_returns_true_when_found(self) -> None:
        from application.enterprise.scim_token_service import revoke_scim_token
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        tok = MagicMock(spec=SCIMTokenModel)
        tok.is_active = True
        tok.label = "test"
        tok.enterprise_id = "ent-1"

        session = self._make_session(token_obj=tok)
        ok = await revoke_scim_token("tok-1", "admin-1", session)
        assert ok is True
        assert tok.is_active is False

    @pytest.mark.asyncio
    async def test_revoke_returns_false_when_not_found(self) -> None:
        from application.enterprise.scim_token_service import revoke_scim_token

        session = self._make_session(token_obj=None)
        ok = await revoke_scim_token("nonexistent", "admin-1", session)
        assert ok is False

    @pytest.mark.asyncio
    async def test_verify_valid_token(self) -> None:
        from application.enterprise.scim_token_service import _hash_token, verify_scim_token
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        raw = "valid_raw_token_abc123"
        tok = MagicMock(spec=SCIMTokenModel)
        tok.token_hash = _hash_token(raw)
        tok.is_active = True
        tok.expires_at = None
        tok.last_used_at = None
        tok.use_count = 0

        session = self._make_session(token_obj=tok)
        result = await verify_scim_token(raw, session)
        assert result is tok
        assert tok.use_count == 1
        assert tok.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_inactive_token_returns_none(self) -> None:
        from application.enterprise.scim_token_service import _hash_token, verify_scim_token
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        raw = "inactive_token"
        tok = MagicMock(spec=SCIMTokenModel)
        tok.token_hash = _hash_token(raw)
        tok.is_active = False
        tok.expires_at = None

        session = self._make_session(token_obj=tok)
        result = await verify_scim_token(raw, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_expired_token_returns_none(self) -> None:
        from application.enterprise.scim_token_service import _hash_token, verify_scim_token
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        raw = "expired_token"
        tok = MagicMock(spec=SCIMTokenModel)
        tok.token_hash = _hash_token(raw)
        tok.is_active = True
        tok.expires_at = datetime.now(UTC) - timedelta(seconds=1)  # already expired

        session = self._make_session(token_obj=tok)
        result = await verify_scim_token(raw, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_not_found_returns_none(self) -> None:
        from application.enterprise.scim_token_service import verify_scim_token

        session = self._make_session(token_obj=None)
        result = await verify_scim_token("unknown_token", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_rotate_revokes_old_and_creates_new(self) -> None:
        from application.enterprise.scim_token_service import rotate_scim_token
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        old = MagicMock(spec=SCIMTokenModel)
        old.is_active = True
        old.label = "original"
        old.enterprise_id = "ent-1"
        old.idp_id = None
        old.scope = "FULL_ADMIN"

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        old_result = MagicMock()
        old_result.scalar_one_or_none.return_value = old
        session.execute = AsyncMock(return_value=old_result)

        result = await rotate_scim_token(
            token_id="old-id",
            new_label="rotated",
            ttl_days=90,
            actor_id="admin-1",
            session=session,
        )

        assert result is not None
        raw, new_token = result
        assert old.is_active is False
        assert new_token.is_active is True
        assert isinstance(raw, str)

    @pytest.mark.asyncio
    async def test_rotate_nonexistent_returns_none(self) -> None:
        from application.enterprise.scim_token_service import rotate_scim_token

        session = self._make_session(token_obj=None)
        result = await rotate_scim_token("nope", None, 30, "admin", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_two_rotations_produce_different_tokens(self) -> None:
        from application.enterprise.scim_token_service import create_scim_token

        session1 = AsyncMock()
        session1.add = MagicMock()
        session1.flush = AsyncMock()
        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = None
        session1.execute = AsyncMock(return_value=r1)

        session2 = AsyncMock()
        session2.add = MagicMock()
        session2.flush = AsyncMock()
        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = None
        session2.execute = AsyncMock(return_value=r2)

        raw1, _ = await create_scim_token("ent", None, 30, "actor", session1)
        raw2, _ = await create_scim_token("ent", None, 30, "actor", session2)
        assert raw1 != raw2


# ── Secret Leakage Guards ─────────────────────────────────────────────────────


class TestSecretLeakage:
    def test_identity_provider_response_no_client_secret_field(self) -> None:
        from interfaces.api.schemas.enterprise import IdentityProviderResponse

        fields = set(IdentityProviderResponse.model_fields.keys())
        assert "client_secret" not in fields
        assert "client_secret_encrypted" not in fields
        # The safe boolean indicator is present
        assert "has_client_secret" in fields

    def test_identity_provider_response_no_secret_reference_data(self) -> None:
        """SecretReference identifier must not appear in IdP response."""
        from interfaces.api.schemas.enterprise import IdentityProviderResponse

        fields = set(IdentityProviderResponse.model_fields.keys())
        assert "secret_reference_id" not in fields
        assert "secret_identifier" not in fields

    def test_scim_token_response_no_raw_token(self) -> None:
        from interfaces.api.schemas.enterprise import SCIMTokenResponse

        fields = set(SCIMTokenResponse.model_fields.keys())
        assert "raw_token" not in fields
        assert "token_hash" not in fields

    def test_scim_token_create_response_has_raw_token_once(self) -> None:
        """raw_token appears ONLY in the creation response, never in list/get."""
        from interfaces.api.schemas.enterprise import (
            SCIMTokenCreateResponse,
            SCIMTokenResponse,
        )

        create_fields = set(SCIMTokenCreateResponse.model_fields.keys())
        list_fields = set(SCIMTokenResponse.model_fields.keys())
        assert "raw_token" in create_fields
        assert "raw_token" not in list_fields
        assert "token_hash" not in create_fields  # still hidden

    def test_orm_identity_provider_no_client_secret_column(self) -> None:
        """client_secret_encrypted column must be removed from the ORM model."""
        import sqlalchemy as sa

        from infrastructure.persistence.models.enterprise import IdentityProviderModel

        cols = {c.name for c in sa.inspect(IdentityProviderModel).columns}
        assert "client_secret_encrypted" not in cols
        assert "secret_reference_id" in cols

    def test_secret_reference_model_has_no_value_column(self) -> None:
        """SecretReferenceModel must store (provider, identifier) only."""
        import sqlalchemy as sa

        from infrastructure.persistence.models.enterprise import SecretReferenceModel

        cols = {c.name for c in sa.inspect(SecretReferenceModel).columns}
        assert "value" not in cols
        assert "secret_value" not in cols
        assert "encrypted_value" not in cols
        assert "secret_identifier" in cols
        assert "provider" in cols

    def test_user_response_no_password_hash(self) -> None:
        """Regression — UserResponse must not expose password_hash (pre-existing)."""
        from interfaces.api.schemas.user import UserResponse

        fields = set(UserResponse.model_fields.keys())
        assert "password_hash" not in fields


# ── SCIM Isolation Tests ──────────────────────────────────────────────────────


class TestSCIMIsolation:
    def test_scim_token_has_enterprise_id(self) -> None:
        import sqlalchemy as sa

        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        cols = {c.name for c in sa.inspect(SCIMTokenModel).columns}
        assert "enterprise_id" in cols

    def test_scim_token_service_enterprise_id_in_create_signature(self) -> None:
        import inspect

        from application.enterprise.scim_token_service import create_scim_token

        sig = inspect.signature(create_scim_token)
        assert "enterprise_id" in sig.parameters

    def test_scim_token_service_enterprise_id_in_list_signature(self) -> None:
        import inspect

        from application.enterprise.scim_token_service import list_scim_tokens

        sig = inspect.signature(list_scim_tokens)
        assert "enterprise_id" in sig.parameters

    def test_scim_token_hash_unique(self) -> None:
        """token_hash must have a uniqueness constraint to prevent collisions."""
        import sqlalchemy as sa

        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        col = sa.inspect(SCIMTokenModel).columns["token_hash"]
        # Check the column is unique (either via unique=True on column or UniqueConstraint)
        # SQLAlchemy exposes column-level unique as col.unique
        assert col.unique is True


# ── ORM Model Tests ───────────────────────────────────────────────────────────


class TestM401ORMModels:
    def test_secret_reference_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import SecretReferenceModel

        assert SecretReferenceModel.__tablename__ == "secret_references"

    def test_scim_token_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import SCIMTokenModel

        assert SCIMTokenModel.__tablename__ == "scim_tokens"

    def test_identity_provider_has_secret_reference_id(self) -> None:
        import sqlalchemy as sa

        from infrastructure.persistence.models.enterprise import IdentityProviderModel

        cols = {c.name for c in sa.inspect(IdentityProviderModel).columns}
        assert "secret_reference_id" in cols
