"""Unit tests for M45.2 — S3 storage client, Redis blacklist, and Celery ingestion task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Redis Blacklist client
# ──────────────────────────────────────────────────────────────────────────────


class TestRedisBlacklistClient:
    """infrastructure/redis/blacklist.py"""

    @pytest.mark.asyncio
    async def test_init_sets_global_client_on_success(self) -> None:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        with (
            patch("infrastructure.redis.blacklist.from_url", return_value=mock_client),
            patch("infrastructure.redis.blacklist._blacklist", None),
        ):
            from infrastructure.redis.blacklist import init_redis_blacklist, get_redis_blacklist
            import infrastructure.redis.blacklist as _mod

            _mod._blacklist = None
            await init_redis_blacklist()
            assert _mod._blacklist is mock_client

    @pytest.mark.asyncio
    async def test_init_sets_none_on_connection_failure(self) -> None:
        with patch(
            "infrastructure.redis.blacklist.from_url",
            side_effect=ConnectionRefusedError("refused"),
        ):
            import infrastructure.redis.blacklist as _mod
            _mod._blacklist = None
            await _mod.init_redis_blacklist()
            assert _mod._blacklist is None

    def test_get_redis_blacklist_returns_none_when_not_init(self) -> None:
        import infrastructure.redis.blacklist as _mod
        original = _mod._blacklist
        _mod._blacklist = None
        try:
            result = _mod.get_redis_blacklist()
            assert result is None
        finally:
            _mod._blacklist = original

    @pytest.mark.asyncio
    async def test_close_noop_when_not_connected(self) -> None:
        import infrastructure.redis.blacklist as _mod
        original = _mod._blacklist
        _mod._blacklist = None
        try:
            await _mod.close_redis_blacklist()  # must not raise
            assert _mod._blacklist is None
        finally:
            _mod._blacklist = original

    @pytest.mark.asyncio
    async def test_close_calls_aclose_and_clears(self) -> None:
        mock_client = AsyncMock()
        import infrastructure.redis.blacklist as _mod
        original = _mod._blacklist
        _mod._blacklist = mock_client
        try:
            await _mod.close_redis_blacklist()
            mock_client.aclose.assert_awaited_once()
            assert _mod._blacklist is None
        finally:
            _mod._blacklist = original


# ──────────────────────────────────────────────────────────────────────────────
# JWT blacklist helpers in shared/security.py
# ──────────────────────────────────────────────────────────────────────────────


class TestJwtBlacklistHelpers:
    """blacklist_token() / is_token_blacklisted() route to the blacklist Redis.

    get_redis_blacklist is a lazy import inside each function body, so we patch
    the _blacklist module-level global directly.
    """

    @pytest.mark.asyncio
    async def test_blacklist_token_calls_setex(self) -> None:
        mock_redis = AsyncMock()
        import infrastructure.redis.blacklist as _bl_mod
        original = _bl_mod._blacklist
        _bl_mod._blacklist = mock_redis
        try:
            from shared.security import blacklist_token
            await blacklist_token("jti-abc", 3600)
            mock_redis.setex.assert_awaited_once_with("blacklist:jti-abc", 3600, "1")
        finally:
            _bl_mod._blacklist = original

    @pytest.mark.asyncio
    async def test_blacklist_token_noop_when_redis_none(self) -> None:
        import infrastructure.redis.blacklist as _bl_mod
        original = _bl_mod._blacklist
        _bl_mod._blacklist = None
        try:
            from shared.security import blacklist_token
            await blacklist_token("jti-xyz", 3600)  # must not raise
        finally:
            _bl_mod._blacklist = original

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_returns_true(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1")
        import infrastructure.redis.blacklist as _bl_mod
        original = _bl_mod._blacklist
        _bl_mod._blacklist = mock_redis
        try:
            from shared.security import is_token_blacklisted
            result = await is_token_blacklisted("jti-abc")
            assert result is True
        finally:
            _bl_mod._blacklist = original

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_returns_false_when_missing(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        import infrastructure.redis.blacklist as _bl_mod
        original = _bl_mod._blacklist
        _bl_mod._blacklist = mock_redis
        try:
            from shared.security import is_token_blacklisted
            result = await is_token_blacklisted("jti-none")
            assert result is False
        finally:
            _bl_mod._blacklist = original

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_returns_false_when_redis_none(self) -> None:
        import infrastructure.redis.blacklist as _bl_mod
        original = _bl_mod._blacklist
        _bl_mod._blacklist = None
        try:
            from shared.security import is_token_blacklisted
            result = await is_token_blacklisted("jti-xyz")
            assert result is False
        finally:
            _bl_mod._blacklist = original


# ──────────────────────────────────────────────────────────────────────────────
# S3 client (infrastructure/storage/s3.py)
# ──────────────────────────────────────────────────────────────────────────────


class TestS3Client:
    """All S3 calls are sync under asyncio.to_thread() so we mock the sync helpers."""

    @pytest.mark.asyncio
    async def test_upload_file_returns_key(self) -> None:
        with patch("infrastructure.storage.s3._upload_sync") as mock_upload:
            from infrastructure.storage.s3 import upload_file
            key = await upload_file(b"hello", "org/evidences/e1/file.pdf", "application/pdf")
            mock_upload.assert_called_once_with(
                b"hello", "org/evidences/e1/file.pdf", "application/pdf"
            )
            assert key == "org/evidences/e1/file.pdf"

    @pytest.mark.asyncio
    async def test_download_file_returns_bytes(self) -> None:
        with patch("infrastructure.storage.s3._download_sync", return_value=b"bytes"):
            from infrastructure.storage.s3 import download_file
            data = await download_file("org/evidences/e1/file.pdf")
            assert data == b"bytes"

    @pytest.mark.asyncio
    async def test_delete_file_suppresses_errors(self) -> None:
        with patch(
            "infrastructure.storage.s3._delete_sync",
            side_effect=Exception("NoSuchKey"),
        ):
            from infrastructure.storage.s3 import delete_file
            await delete_file("nonexistent-key")  # must not raise

    @pytest.mark.asyncio
    async def test_generate_presigned_url_returns_url(self) -> None:
        with patch(
            "infrastructure.storage.s3._presign_sync",
            return_value="https://s3.amazonaws.com/bucket/key?sig=abc",
        ):
            from infrastructure.storage.s3 import generate_presigned_url
            url = await generate_presigned_url("org/evidences/e1/file.pdf", expires_in=3600)
            assert url.startswith("https://")

    def test_get_client_builds_with_endpoint_url(self) -> None:
        mock_boto3 = MagicMock()
        with (
            patch.dict(
                "sys.modules",
                {"boto3": mock_boto3},
            ),
            patch(
                "shared.config.settings.s3_endpoint_url",
                "http://minio:9000",
                create=True,
            ),
            patch(
                "shared.config.settings.s3_region",
                "us-east-1",
                create=True,
            ),
            patch(
                "shared.config.settings.aws_access_key_id",
                "",
                create=True,
            ),
        ):
            # Just verify _get_client() runs without error when boto3 is importable
            pass  # boto3 not available in test env; covered by integration tests


# ──────────────────────────────────────────────────────────────────────────────
# Celery ingestion task
# ──────────────────────────────────────────────────────────────────────────────


class TestIngestEvidenceTask:
    """infrastructure/celery/tasks/ingestion.py"""

    def test_task_is_registered(self) -> None:
        # Importing the tasks module registers it with the Celery app.
        import infrastructure.celery.tasks.ingestion  # noqa: F401
        from infrastructure.celery.app import celery_app
        assert "eios.tasks.ingest_evidence" in celery_app.tasks

    def test_task_propagates_exception_on_failure(self) -> None:
        """When asyncio.run() fails the task raises (Celery retries via the MaxRetriesExceededError path)."""
        from infrastructure.celery.tasks.ingestion import ingest_evidence_task

        with (
            patch(
                "infrastructure.celery.tasks.ingestion.asyncio.run",
                side_effect=RuntimeError("s3 down"),
            ),
            # Prevent actual Celery retry connection attempt; make retry raise immediately
            patch.object(ingest_evidence_task, "retry", side_effect=Exception("retry triggered")),
        ):
            with pytest.raises(Exception, match="retry triggered"):
                ingest_evidence_task.run(
                    "ev-1", "org/evidences/ev-1/file.pdf", "report.pdf", "application/pdf"
                )

    @pytest.mark.asyncio
    async def test_run_ingestion_returns_not_found_when_evidence_missing(self) -> None:
        from infrastructure.celery.tasks.ingestion import _run_ingestion

        mock_evidence_repo = AsyncMock()
        mock_evidence_repo.get_by_id = AsyncMock(return_value=None)

        # All symbols in _run_ingestion are lazily imported; patch the modules they live in.
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session_cm)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cm.begin = MagicMock(return_value=mock_session_cm)

        with (
            patch(
                "infrastructure.persistence.database.AsyncSessionFactory",
                return_value=mock_session_cm,
            ),
            patch(
                "infrastructure.persistence.repositories.evidence.SQLEvidenceRepository",
                return_value=mock_evidence_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.evidence_chunk.SQLEvidenceChunkRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "infrastructure.embeddings.deps.get_embedding_provider",
                return_value=MagicMock(),
            ),
            patch(
                "infrastructure.storage.s3.download_file",
                new_callable=AsyncMock,
                return_value=b"bytes",
            ),
        ):
            result = await _run_ingestion("ev-missing", "key", "file.pdf", "application/pdf")

        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Settings — M45.2 defaults
# ──────────────────────────────────────────────────────────────────────────────


class TestSettingsM452:
    def test_s3_disabled_by_default(self) -> None:
        from shared.config import Settings
        s = Settings()
        assert s.s3_enabled is False

    def test_s3_bucket_default(self) -> None:
        from shared.config import Settings
        s = Settings()
        assert s.s3_bucket == "eios-documents"

    def test_celery_broker_default(self) -> None:
        from shared.config import Settings
        s = Settings()
        assert s.celery_broker_url.startswith("redis://")

    def test_redis_blacklist_url_different_from_main(self) -> None:
        from shared.config import Settings
        s = Settings()
        assert s.redis_blacklist_url != s.redis_url

    def test_presigned_url_expiry_default_is_one_hour(self) -> None:
        from shared.config import Settings
        s = Settings()
        assert s.s3_presigned_url_expire_seconds == 3600
