"""Celery maintenance tasks — backup health check + replication lag monitor (M45.3).

Scheduled via Celery Beat (configured in infrastructure/celery/app.py).

Tasks:
  check_backup_health  — verifies a pg_basebackup marker exists and is < 25h old.
                         Logs a WARNING (and in future can alert via webhook) if stale.
  check_replication_lag — queries pg_stat_replication on the primary to measure lag.
                          Logs WARNING if lag exceeds the configured threshold.

Both tasks are non-critical background monitors — they never mutate application data.
"""

from __future__ import annotations

import asyncio

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)

# Alert threshold: warn if last successful backup is older than this many seconds.
_BACKUP_STALE_THRESHOLD_SECONDS = 25 * 3600  # 25 hours

# Alert threshold: warn if replication lag exceeds this many bytes.
_REPLICATION_LAG_WARN_BYTES = 64 * 1024 * 1024  # 64 MiB


@celery_app.task(
    name="eios.maintenance.check_backup_health",
    max_retries=0,
    ignore_result=False,
)
def check_backup_health() -> dict[str, object]:
    """Verify that a recent pg_basebackup marker exists (local or S3)."""
    return asyncio.run(_check_backup_health_async())


@celery_app.task(
    name="eios.maintenance.check_replication_lag",
    max_retries=0,
    ignore_result=False,
)
def check_replication_lag() -> dict[str, object]:
    """Query pg_stat_replication on the primary and report lag metrics."""
    return asyncio.run(_check_replication_lag_async())


# ── Async implementations ──────────────────────────────────────────────────────


async def _check_backup_health_async() -> dict[str, object]:
    import os  # noqa: PLC0415
    from datetime import UTC, datetime  # noqa: PLC0415

    from shared.config import settings  # noqa: PLC0415

    backup_dir = os.environ.get("BACKUP_DIR", "/var/backups/eios/postgres")
    marker_path = os.path.join(backup_dir, ".last_backup_timestamp")

    # ── Local marker ──────────────────────────────────────────────────────────
    if os.path.exists(marker_path):
        try:
            with open(marker_path) as fh:
                ts_str = fh.read().strip()
            last_backup = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            age_seconds = (datetime.now(UTC) - last_backup).total_seconds()

            if age_seconds > _BACKUP_STALE_THRESHOLD_SECONDS:
                logger.warning(
                    "backup_stale",
                    last_backup=ts_str,
                    age_hours=round(age_seconds / 3600, 1),
                    threshold_hours=_BACKUP_STALE_THRESHOLD_SECONDS / 3600,
                )
                return {"status": "stale", "last_backup": ts_str, "age_seconds": age_seconds}

            logger.info(
                "backup_healthy", last_backup=ts_str, age_hours=round(age_seconds / 3600, 1)
            )
            return {"status": "healthy", "last_backup": ts_str, "age_seconds": age_seconds}
        except Exception as exc:  # noqa: BLE001
            logger.warning("backup_marker_unreadable", path=marker_path, error=str(exc))

    # ── S3 marker fallback ────────────────────────────────────────────────────
    if settings.s3_enabled:
        try:
            from infrastructure.storage.s3 import download_file  # noqa: PLC0415

            s3_bucket_key = f"{settings.s3_bucket}/.last_backup_timestamp"
            content = await download_file(s3_bucket_key)
            ts_str = content.decode().strip()
            from datetime import UTC, datetime  # noqa: PLC0415, F811

            last_backup = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            age_seconds = (datetime.now(UTC) - last_backup).total_seconds()
            status = "stale" if age_seconds > _BACKUP_STALE_THRESHOLD_SECONDS else "healthy"
            if status == "stale":
                logger.warning("backup_stale_s3", last_backup=ts_str, age_seconds=age_seconds)
            else:
                logger.info("backup_healthy_s3", last_backup=ts_str)
            return {
                "status": status,
                "last_backup": ts_str,
                "age_seconds": age_seconds,
                "source": "s3",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("backup_s3_marker_missing", error=str(exc))

    logger.warning("backup_marker_not_found", backup_dir=backup_dir)
    return {"status": "unknown", "detail": "No backup marker found — run pg_backup.sh first"}


async def _check_replication_lag_async() -> dict[str, object]:
    from sqlalchemy import text  # noqa: PLC0415

    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from shared.config import settings  # noqa: PLC0415

    if not settings.database_readonly_url:
        return {
            "status": "skipped",
            "detail": "No read replica configured (DATABASE_READONLY_URL not set)",
        }

    replication_sql = text("""
        SELECT
            application_name,
            state,
            sent_lsn::text,
            write_lsn::text,
            flush_lsn::text,
            replay_lsn::text,
            (sent_lsn - replay_lsn) AS lag_bytes,
            write_lag,
            flush_lag,
            replay_lag,
            sync_state
        FROM pg_stat_replication
        ORDER BY lag_bytes DESC NULLS LAST
    """)

    async with AsyncSessionFactory() as session:
        result = await session.execute(replication_sql)
        rows = result.mappings().all()

    if not rows:
        logger.warning("replication_no_standbys", detail="No standbys connected to primary")
        return {"status": "no_standbys", "standbys": []}

    standbys = []
    max_lag = 0
    for row in rows:
        lag_bytes = int(row["lag_bytes"] or 0)
        max_lag = max(max_lag, lag_bytes)
        entry = {
            "application_name": row["application_name"],
            "state": row["state"],
            "lag_bytes": lag_bytes,
            "write_lag": str(row["write_lag"]) if row["write_lag"] else None,
            "flush_lag": str(row["flush_lag"]) if row["flush_lag"] else None,
            "replay_lag": str(row["replay_lag"]) if row["replay_lag"] else None,
            "sync_state": row["sync_state"],
        }
        standbys.append(entry)

    status = "healthy"
    if max_lag > _REPLICATION_LAG_WARN_BYTES:
        status = "lag_warning"
        logger.warning(
            "replication_lag_high",
            max_lag_bytes=max_lag,
            max_lag_mb=round(max_lag / 1024 / 1024, 1),
            threshold_mb=_REPLICATION_LAG_WARN_BYTES / 1024 / 1024,
        )
    else:
        logger.info("replication_healthy", max_lag_bytes=max_lag, standbys=len(standbys))

    return {"status": status, "max_lag_bytes": max_lag, "standbys": standbys}
