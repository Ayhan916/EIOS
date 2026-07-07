"""Unit tests for M45.3 — PgBouncer, Read Replica, Backup & DR."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Settings — M45.3 read-replica default
# ──────────────────────────────────────────────────────────────────────────────


class TestSettingsM453:
    def test_database_readonly_url_default_is_empty(self) -> None:
        from shared.config import Settings

        s = Settings()
        assert s.database_readonly_url == ""

    def test_database_readonly_url_can_be_set(self) -> None:
        from shared.config import Settings

        s = Settings(database_readonly_url="postgresql+asyncpg://eios:pw@replica:5432/eios_db")
        assert "replica" in s.database_readonly_url

    def test_production_validation_passes_with_readonly_url(self) -> None:
        from shared.config import Settings

        s = Settings(
            environment="production",
            secret_key="a-very-long-and-secure-secret-key-for-testing-purposes",
            allowed_origins=["https://app.eios.io"],
            redis_url="redis://:secret@redis.internal:6379/0",
            redis_blacklist_url="redis://:secret@redis-blacklist.internal:6379/0",
            database_readonly_url="postgresql+asyncpg://eios:pw@postgres-replica:5432/eios_db",
        )
        s.validate_production()  # must not raise


# ──────────────────────────────────────────────────────────────────────────────
# database.py — read-only session factory
# ──────────────────────────────────────────────────────────────────────────────


class TestReadOnlySessionFactory:
    def test_get_readonly_session_is_async_generator(self) -> None:
        import inspect

        from infrastructure.persistence.database import get_readonly_session

        assert inspect.isasyncgenfunction(get_readonly_session)

    def test_readonly_session_factory_exists(self) -> None:
        from infrastructure.persistence.database import ReadOnlyAsyncSessionFactory

        assert ReadOnlyAsyncSessionFactory is not None

    def test_falls_back_to_primary_when_readonly_url_not_set(self) -> None:
        """When DATABASE_READONLY_URL is empty, readonly engine == primary engine."""
        from infrastructure.persistence.database import _readonly_engine, engine
        from shared.config import settings

        if not settings.database_readonly_url:
            assert _readonly_engine is engine

    @pytest.mark.asyncio
    async def test_get_readonly_session_yields_async_session(self) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession

        from infrastructure.persistence.database import get_readonly_session

        # Patch the readonly session factory to avoid actual DB connection
        mock_session = AsyncMock(spec=AsyncSession)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "infrastructure.persistence.database.ReadOnlyAsyncSessionFactory",
            return_value=mock_cm,
        ):
            async for session in get_readonly_session():
                assert session is mock_session


# ──────────────────────────────────────────────────────────────────────────────
# Celery maintenance tasks
# ──────────────────────────────────────────────────────────────────────────────


class TestMaintenanceTasksRegistered:
    def test_backup_health_task_registered(self) -> None:
        import infrastructure.celery.tasks.maintenance  # noqa: F401
        from infrastructure.celery.app import celery_app

        assert "eios.maintenance.check_backup_health" in celery_app.tasks

    def test_replication_lag_task_registered(self) -> None:
        import infrastructure.celery.tasks.maintenance  # noqa: F401
        from infrastructure.celery.app import celery_app

        assert "eios.maintenance.check_replication_lag" in celery_app.tasks

    def test_beat_schedule_contains_backup_check(self) -> None:
        from infrastructure.celery.app import celery_app

        assert "check-backup-health-daily" in celery_app.conf.beat_schedule

    def test_beat_schedule_contains_replication_check(self) -> None:
        from infrastructure.celery.app import celery_app

        assert "check-replication-lag-hourly" in celery_app.conf.beat_schedule

    def test_backup_check_runs_daily(self) -> None:
        from infrastructure.celery.app import celery_app

        schedule = celery_app.conf.beat_schedule["check-backup-health-daily"]
        assert schedule["schedule"] == 86400

    def test_replication_check_runs_hourly(self) -> None:
        from infrastructure.celery.app import celery_app

        schedule = celery_app.conf.beat_schedule["check-replication-lag-hourly"]
        assert schedule["schedule"] == 3600


class TestCheckBackupHealth:
    @pytest.mark.asyncio
    async def test_returns_healthy_when_marker_fresh(self, tmp_path) -> None:
        from infrastructure.celery.tasks.maintenance import _check_backup_health_async

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        marker = tmp_path / ".last_backup_timestamp"
        marker.write_text(ts)

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            result = await _check_backup_health_async()

        assert result["status"] == "healthy"
        assert result["last_backup"] == ts

    @pytest.mark.asyncio
    async def test_returns_stale_when_marker_old(self, tmp_path) -> None:
        from infrastructure.celery.tasks.maintenance import _check_backup_health_async

        old_ts = (datetime.now(UTC) - timedelta(hours=30)).strftime("%Y%m%dT%H%M%SZ")
        marker = tmp_path / ".last_backup_timestamp"
        marker.write_text(old_ts)

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            result = await _check_backup_health_async()

        assert result["status"] == "stale"

    @pytest.mark.asyncio
    async def test_returns_unknown_when_no_marker(self, tmp_path) -> None:
        from infrastructure.celery.tasks.maintenance import _check_backup_health_async

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            result = await _check_backup_health_async()

        assert result["status"] == "unknown"
        assert "No backup marker" in result["detail"]

    @pytest.mark.asyncio
    async def test_returns_stale_when_marker_unreadable(self, tmp_path) -> None:
        from infrastructure.celery.tasks.maintenance import _check_backup_health_async

        marker = tmp_path / ".last_backup_timestamp"
        marker.write_text("NOT_A_TIMESTAMP")  # invalid format

        with patch.dict(os.environ, {"BACKUP_DIR": str(tmp_path)}):
            result = await _check_backup_health_async()

        # Falls through to "unknown" since local marker is unreadable and S3 disabled
        assert result["status"] in ("unknown", "stale")


class TestCheckReplicationLag:
    """settings and AsyncSessionFactory are lazily imported — patch at their source modules."""

    @pytest.mark.asyncio
    async def test_skipped_when_no_readonly_url(self) -> None:
        import shared.config as _cfg_mod
        from infrastructure.celery.tasks.maintenance import _check_replication_lag_async

        original_url = _cfg_mod.settings.database_readonly_url
        _cfg_mod.settings.database_readonly_url = ""
        try:
            result = await _check_replication_lag_async()
        finally:
            _cfg_mod.settings.database_readonly_url = original_url

        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_healthy_when_lag_below_threshold(self) -> None:
        from infrastructure.celery.tasks.maintenance import _check_replication_lag_async

        mock_row = {
            "application_name": "replica1",
            "state": "streaming",
            "sent_lsn": "0/5000000",
            "write_lsn": "0/5000000",
            "flush_lsn": "0/5000000",
            "replay_lsn": "0/5000000",
            "lag_bytes": 1024,
            "write_lag": None,
            "flush_lag": None,
            "replay_lag": None,
            "sync_state": "async",
        }
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        import infrastructure.persistence.database as _db_mod
        import shared.config as _cfg_mod

        original_url = _cfg_mod.settings.database_readonly_url
        original_factory = _db_mod.AsyncSessionFactory
        _cfg_mod.settings.database_readonly_url = (
            "postgresql+asyncpg://eios:pw@replica:5432/eios_db"
        )
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session_cm)
        try:
            result = await _check_replication_lag_async()
        finally:
            _cfg_mod.settings.database_readonly_url = original_url
            _db_mod.AsyncSessionFactory = original_factory

        assert result["status"] == "healthy"
        assert result["max_lag_bytes"] == 1024
        assert len(result["standbys"]) == 1

    @pytest.mark.asyncio
    async def test_lag_warning_when_lag_exceeds_threshold(self) -> None:
        from infrastructure.celery.tasks.maintenance import (
            _REPLICATION_LAG_WARN_BYTES,
            _check_replication_lag_async,
        )

        mock_row = {
            "application_name": "replica1",
            "state": "streaming",
            "sent_lsn": "0/5000000",
            "write_lsn": "0/4000000",
            "flush_lsn": "0/4000000",
            "replay_lsn": "0/4000000",
            "lag_bytes": _REPLICATION_LAG_WARN_BYTES + 1,
            "write_lag": "00:00:05",
            "flush_lag": "00:00:05",
            "replay_lag": "00:00:05",
            "sync_state": "async",
        }
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [mock_row]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        import infrastructure.persistence.database as _db_mod
        import shared.config as _cfg_mod

        original_url = _cfg_mod.settings.database_readonly_url
        original_factory = _db_mod.AsyncSessionFactory
        _cfg_mod.settings.database_readonly_url = (
            "postgresql+asyncpg://eios:pw@replica:5432/eios_db"
        )
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session_cm)
        try:
            result = await _check_replication_lag_async()
        finally:
            _cfg_mod.settings.database_readonly_url = original_url
            _db_mod.AsyncSessionFactory = original_factory

        assert result["status"] == "lag_warning"

    @pytest.mark.asyncio
    async def test_no_standbys_warning(self) -> None:
        from infrastructure.celery.tasks.maintenance import _check_replication_lag_async

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        import infrastructure.persistence.database as _db_mod
        import shared.config as _cfg_mod

        original_url = _cfg_mod.settings.database_readonly_url
        original_factory = _db_mod.AsyncSessionFactory
        _cfg_mod.settings.database_readonly_url = (
            "postgresql+asyncpg://eios:pw@replica:5432/eios_db"
        )
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session_cm)
        try:
            result = await _check_replication_lag_async()
        finally:
            _cfg_mod.settings.database_readonly_url = original_url
            _db_mod.AsyncSessionFactory = original_factory

        assert result["status"] == "no_standbys"
        assert result["standbys"] == []


# ──────────────────────────────────────────────────────────────────────────────
# PgBouncer — session mode constraint documented in config
# ──────────────────────────────────────────────────────────────────────────────


class TestPgBouncerConfig:
    def test_config_file_exists(self) -> None:
        config_path = (
            "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/pgbouncer/pgbouncer.ini"
        )
        assert os.path.exists(config_path)

    def test_config_uses_session_mode(self) -> None:
        config_path = (
            "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/pgbouncer/pgbouncer.ini"
        )
        content = open(config_path).read()
        assert "pool_mode = session" in content

    def test_userlist_template_exists(self) -> None:
        template_path = (
            "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/pgbouncer/userlist.txt.template"
        )
        assert os.path.exists(template_path)
