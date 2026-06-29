"""Unit tests for M47 — Multi-Region Data Residency & Geo-Routing.

Covers:
  - RegionRouter: session factory selection, S3 bucket, Celery queue, AWS region
  - RegionRouter: canonical(), is_local_region(), fallback behaviour
  - DataResidencyAuditLogModel: fields, tablename, immutable (no BaseModel inheritance)
  - RegionEnforcementMiddleware: advisory-only, no blocking
  - enforce_data_residency dep: strict mode 451, advisory pass-through
  - dispatch_to_region: correct queue selection
  - Migration 058: revision chain, table creation, index creation
  - Config: new M47 settings present with correct defaults
"""

from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# RegionRouter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRegionRouter:
    def _router_with(self, instance_region="US", **kwargs):
        """Return a fresh RegionRouter with mocked settings."""
        import infrastructure.routing.region_router as mod

        fake_settings = MagicMock()
        fake_settings.instance_region = instance_region
        fake_settings.database_url = "postgresql+asyncpg://user:pw@localhost/db"
        fake_settings.region_db_eu_url = kwargs.get("eu_url", "")
        fake_settings.region_db_us_url = kwargs.get("us_url", "")
        fake_settings.region_db_apac_url = kwargs.get("apac_url", "")
        fake_settings.s3_bucket = "eios-global"
        fake_settings.region_s3_bucket_eu = kwargs.get("s3_eu", "")
        fake_settings.region_s3_bucket_us = kwargs.get("s3_us", "")
        fake_settings.region_s3_bucket_apac = kwargs.get("s3_apac", "")
        fake_settings.s3_region = "us-east-1"
        fake_settings.db_pool_size = 5
        fake_settings.db_pool_max_overflow = 10
        fake_settings.db_pool_timeout = 30

        original_settings = mod.settings
        mod.settings = fake_settings
        # Clear the LRU cache so new settings take effect
        mod._build_session_factory.cache_clear()
        try:
            from infrastructure.routing.region_router import RegionRouter
            router = RegionRouter()
            yield router
        finally:
            mod.settings = original_settings
            mod._build_session_factory.cache_clear()

    def test_canonical_eu(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.canonical("eu") == "EU"
        assert r.canonical("EU") == "EU"

    def test_canonical_unknown_falls_back_to_instance_region(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "US"
        try:
            r = RegionRouter()
            assert r.canonical("INVALID") == "US"
            assert r.canonical(None) == "US"
        finally:
            cfg_mod.settings.instance_region = original

    def test_is_local_region_match(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "EU"
        try:
            r = RegionRouter()
            assert r.is_local_region("EU") is True
            assert r.is_local_region("eu") is True
        finally:
            cfg_mod.settings.instance_region = original

    def test_is_local_region_mismatch(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "US"
        try:
            r = RegionRouter()
            assert r.is_local_region("EU") is False
        finally:
            cfg_mod.settings.instance_region = original

    def test_celery_queue_eu(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.get_celery_queue("EU") == "eios-eu"

    def test_celery_queue_us(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.get_celery_queue("US") == "eios-us"

    def test_celery_queue_apac(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.get_celery_queue("APAC") == "eios-apac"

    def test_celery_queue_unknown_falls_back(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "US"
        try:
            r = RegionRouter()
            assert r.get_celery_queue(None) == "eios-us"  # falls back to instance region
        finally:
            cfg_mod.settings.instance_region = original

    def test_s3_bucket_regional_configured(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original_eu = cfg_mod.settings.region_s3_bucket_eu
        cfg_mod.settings.region_s3_bucket_eu = "eios-docs-eu"
        try:
            r = RegionRouter()
            assert r.get_s3_bucket("EU") == "eios-docs-eu"
        finally:
            cfg_mod.settings.region_s3_bucket_eu = original_eu

    def test_s3_bucket_falls_back_to_global(self):
        from infrastructure.routing.region_router import RegionRouter
        import shared.config as cfg_mod
        original_eu = cfg_mod.settings.region_s3_bucket_eu
        original_global = cfg_mod.settings.s3_bucket
        cfg_mod.settings.region_s3_bucket_eu = ""
        cfg_mod.settings.s3_bucket = "eios-global"
        try:
            r = RegionRouter()
            assert r.get_s3_bucket("EU") == "eios-global"
        finally:
            cfg_mod.settings.region_s3_bucket_eu = original_eu
            cfg_mod.settings.s3_bucket = original_global

    def test_get_aws_region_eu(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.get_aws_region("EU") == "eu-west-1"

    def test_get_aws_region_apac(self):
        from infrastructure.routing.region_router import RegionRouter
        r = RegionRouter()
        assert r.get_aws_region("APAC") == "ap-southeast-1"

    def test_session_factory_returns_sessionmaker(self):
        from infrastructure.routing.region_router import RegionRouter
        from sqlalchemy.ext.asyncio import async_sessionmaker
        r = RegionRouter()
        factory = r.get_session_factory("US")
        assert isinstance(factory, async_sessionmaker)

    def test_session_factory_cached_for_same_url(self):
        from infrastructure.routing.region_router import RegionRouter, _build_session_factory
        r = RegionRouter()
        f1 = r.get_session_factory("US")
        f2 = r.get_session_factory("US")
        assert f1 is f2  # same URL → same cached factory


# ─────────────────────────────────────────────────────────────────────────────
# DataResidencyAuditLogModel
# ─────────────────────────────────────────────────────────────────────────────

class TestDataResidencyAuditLogModel:
    def test_tablename(self):
        from infrastructure.persistence.models.region import DataResidencyAuditLogModel
        assert DataResidencyAuditLogModel.__tablename__ == "data_residency_audit_log"

    def test_required_columns(self):
        from infrastructure.persistence.models.region import DataResidencyAuditLogModel
        cols = {c.key for c in DataResidencyAuditLogModel.__table__.columns}
        for field in ("id", "instance_region", "event_type", "created_at"):
            assert field in cols

    def test_optional_columns(self):
        from infrastructure.persistence.models.region import DataResidencyAuditLogModel
        cols = {c.key for c in DataResidencyAuditLogModel.__table__.columns}
        for field in ("organization_id", "user_id", "org_region", "ip_address", "user_agent"):
            assert field in cols
            col = DataResidencyAuditLogModel.__table__.c[field]
            assert col.nullable is True, f"{field} should be nullable"

    def test_does_not_inherit_base_model(self):
        """Audit log is append-only — must NOT inherit the mutable BaseModel."""
        from infrastructure.persistence.models.region import DataResidencyAuditLogModel
        from infrastructure.persistence.models.base import BaseModel
        assert not issubclass(DataResidencyAuditLogModel, BaseModel), (
            "DataResidencyAuditLogModel must use Base (not BaseModel) — it is append-only"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Middleware advisory logging
# ─────────────────────────────────────────────────────────────────────────────

class TestRegionEnforcementMiddleware:
    def _make_request(self, *, path="/api/v1/assessments", org_id=None, data_residency=None, user_id=None):
        request = MagicMock()
        request.url.path = path
        request.method = "GET"
        request.headers = {}
        request.client = None
        state = MagicMock()
        state.organization_id = org_id
        state.data_residency = data_residency
        state.user_id = user_id
        request.state = state
        return request

    def test_skip_path_no_audit(self):
        from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware

        mw = RegionEnforcementMiddleware(app=MagicMock())
        request = self._make_request(path="/health")
        call_next = AsyncMock(return_value=MagicMock())

        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_called_once()

    def test_no_org_id_passes_through(self):
        from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware

        mw = RegionEnforcementMiddleware(app=MagicMock())
        request = self._make_request(org_id=None)
        call_next = AsyncMock(return_value=MagicMock())

        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_called_once()

    def test_local_region_no_audit_task(self):
        """Local-region requests do NOT create audit tasks."""
        from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware
        import shared.config as cfg_mod

        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "EU"
        try:
            mw = RegionEnforcementMiddleware(app=MagicMock())
            request = self._make_request(org_id="org-1", data_residency="EU")
            call_next = AsyncMock(return_value=MagicMock())

            with patch("asyncio.create_task") as mock_task:
                asyncio.run(mw.dispatch(request, call_next))
                mock_task.assert_not_called()
        finally:
            cfg_mod.settings.instance_region = original

    def test_cross_region_creates_audit_task(self):
        """Cross-region access triggers an asyncio background audit task."""
        from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware
        import shared.config as cfg_mod

        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "US"
        try:
            mw = RegionEnforcementMiddleware(app=MagicMock())
            request = self._make_request(org_id="org-1", data_residency="EU")
            call_next = AsyncMock(return_value=MagicMock())

            with patch("asyncio.create_task") as mock_task:
                asyncio.run(mw.dispatch(request, call_next))
                mock_task.assert_called_once()
        finally:
            cfg_mod.settings.instance_region = original

    def test_advisory_mode_does_not_block(self):
        """Even in cross-region, advisory mode (strict=False) never blocks."""
        from infrastructure.middleware.region_enforcement import RegionEnforcementMiddleware
        import shared.config as cfg_mod

        original_region = cfg_mod.settings.instance_region
        original_strict = cfg_mod.settings.region_enforcement_strict
        cfg_mod.settings.instance_region = "US"
        cfg_mod.settings.region_enforcement_strict = False
        try:
            mw = RegionEnforcementMiddleware(app=MagicMock())
            expected_response = MagicMock()
            expected_response.status_code = 200
            request = self._make_request(org_id="org-1", data_residency="EU")
            call_next = AsyncMock(return_value=expected_response)

            with patch("asyncio.create_task"):
                result = asyncio.run(mw.dispatch(request, call_next))

            # Must return the original response, not a 451
            assert result is expected_response
        finally:
            cfg_mod.settings.instance_region = original_region
            cfg_mod.settings.region_enforcement_strict = original_strict


# ─────────────────────────────────────────────────────────────────────────────
# enforce_data_residency dependency
# ─────────────────────────────────────────────────────────────────────────────

class TestEnforceDataResidencyDep:
    def _make_request(self, org_id=None, data_residency=None):
        request = MagicMock()
        request.state.organization_id = org_id
        request.state.data_residency = data_residency
        return request

    def test_advisory_mode_always_passes(self):
        from infrastructure.middleware.region_enforcement import enforce_data_residency
        import shared.config as cfg_mod

        original = cfg_mod.settings.region_enforcement_strict
        cfg_mod.settings.region_enforcement_strict = False
        try:
            request = self._make_request(org_id="org-1", data_residency="EU")
            # Should not raise
            asyncio.run(enforce_data_residency(request))
        finally:
            cfg_mod.settings.region_enforcement_strict = original

    def test_strict_mode_local_region_passes(self):
        from infrastructure.middleware.region_enforcement import enforce_data_residency
        import shared.config as cfg_mod

        orig_strict = cfg_mod.settings.region_enforcement_strict
        orig_region = cfg_mod.settings.instance_region
        cfg_mod.settings.region_enforcement_strict = True
        cfg_mod.settings.instance_region = "EU"
        try:
            request = self._make_request(org_id="org-1", data_residency="EU")
            asyncio.run(enforce_data_residency(request))  # should not raise
        finally:
            cfg_mod.settings.region_enforcement_strict = orig_strict
            cfg_mod.settings.instance_region = orig_region

    def test_strict_mode_cross_region_raises_451(self):
        from infrastructure.middleware.region_enforcement import enforce_data_residency
        from fastapi import HTTPException
        import shared.config as cfg_mod

        orig_strict = cfg_mod.settings.region_enforcement_strict
        orig_region = cfg_mod.settings.instance_region
        cfg_mod.settings.region_enforcement_strict = True
        cfg_mod.settings.instance_region = "US"
        try:
            request = self._make_request(org_id="org-1", data_residency="EU")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(enforce_data_residency(request))
            assert exc_info.value.status_code == 451
        finally:
            cfg_mod.settings.region_enforcement_strict = orig_strict
            cfg_mod.settings.instance_region = orig_region

    def test_strict_mode_no_org_passes(self):
        """Unauthenticated requests (no org_id) are never blocked."""
        from infrastructure.middleware.region_enforcement import enforce_data_residency
        import shared.config as cfg_mod

        orig_strict = cfg_mod.settings.region_enforcement_strict
        cfg_mod.settings.region_enforcement_strict = True
        try:
            request = self._make_request(org_id=None, data_residency=None)
            asyncio.run(enforce_data_residency(request))  # should not raise
        finally:
            cfg_mod.settings.region_enforcement_strict = orig_strict


# ─────────────────────────────────────────────────────────────────────────────
# Region dispatch helper
# ─────────────────────────────────────────────────────────────────────────────

class TestDispatchToRegion:
    def test_routes_eu_to_eu_queue(self):
        from infrastructure.celery.region_dispatch import dispatch_to_region

        mock_task = MagicMock()
        mock_task.apply_async = MagicMock(return_value=MagicMock())

        dispatch_to_region(mock_task, region="EU", args=["arg1"], kwargs={})
        mock_task.apply_async.assert_called_once()
        _, call_kwargs = mock_task.apply_async.call_args
        assert call_kwargs["queue"] == "eios-eu"

    def test_routes_us_to_us_queue(self):
        from infrastructure.celery.region_dispatch import dispatch_to_region

        mock_task = MagicMock()
        dispatch_to_region(mock_task, region="US", args=[], kwargs={})
        _, ckw = mock_task.apply_async.call_args
        assert ckw["queue"] == "eios-us"

    def test_none_region_falls_back(self):
        from infrastructure.celery.region_dispatch import dispatch_to_region
        import shared.config as cfg_mod

        original = cfg_mod.settings.instance_region
        cfg_mod.settings.instance_region = "APAC"
        try:
            mock_task = MagicMock()
            dispatch_to_region(mock_task, region=None)
            _, ckw = mock_task.apply_async.call_args
            assert ckw["queue"] == "eios-apac"
        finally:
            cfg_mod.settings.instance_region = original

    def test_passes_extra_kwargs_to_apply_async(self):
        from infrastructure.celery.region_dispatch import dispatch_to_region

        mock_task = MagicMock()
        dispatch_to_region(mock_task, region="EU", args=[], kwargs={}, countdown=30)
        _, ckw = mock_task.apply_async.call_args
        assert ckw.get("countdown") == 30


# ─────────────────────────────────────────────────────────────────────────────
# Config defaults
# ─────────────────────────────────────────────────────────────────────────────

class TestM47Config:
    def test_instance_region_default(self):
        from shared.config import settings
        assert hasattr(settings, "instance_region")
        assert settings.instance_region == "US"

    def test_enforcement_strict_default_false(self):
        from shared.config import settings
        assert settings.region_enforcement_strict is False

    def test_regional_db_defaults_empty(self):
        from shared.config import settings
        assert settings.region_db_eu_url == ""
        assert settings.region_db_us_url == ""
        assert settings.region_db_apac_url == ""

    def test_regional_s3_defaults_empty(self):
        from shared.config import settings
        assert settings.region_s3_bucket_eu == ""
        assert settings.region_s3_bucket_us == ""
        assert settings.region_s3_bucket_apac == ""


# ─────────────────────────────────────────────────────────────────────────────
# Migration 058
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration058:
    @staticmethod
    def _load_migration():
        migration_path = (
            pathlib.Path(__file__).parent.parent.parent.parent
            / "alembic" / "versions" / "058_m47_multi_region.py"
        )
        spec = importlib.util.spec_from_file_location("migration_058", migration_path)
        mod = ModuleType("migration_058")

        fake_op = MagicMock()
        fake_alembic_pkg = MagicMock()
        fake_alembic_pkg.op = fake_op

        with patch.dict(sys.modules, {"alembic": fake_alembic_pkg, "alembic.op": fake_op}):
            spec.loader.exec_module(mod)

        return mod, fake_op

    def test_revision_chain(self):
        mod, _ = self._load_migration()
        assert mod.revision == "058"
        assert mod.down_revision == "057"

    def test_upgrade_creates_audit_log_table(self):
        mod, fake_op = self._load_migration()
        mod.upgrade()
        created = [call.args[0] for call in fake_op.create_table.call_args_list]
        assert "data_residency_audit_log" in created

    def test_upgrade_creates_org_residency_index(self):
        mod, fake_op = self._load_migration()
        mod.upgrade()
        index_names = [call.args[0] for call in fake_op.create_index.call_args_list]
        assert "ix_organizations_data_residency" in index_names

    def test_downgrade_drops_table_and_index(self):
        mod, fake_op = self._load_migration()
        mod.downgrade()
        assert fake_op.drop_table.called
        assert fake_op.drop_index.called
