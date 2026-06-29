#!/usr/bin/env bash
# pg_restore.sh — EIOS PostgreSQL restore from pg_basebackup (M45.3)
#
# DR procedure: restore a pg_basebackup snapshot to a fresh PostgreSQL data dir.
#
# Usage:
#   pg_restore.sh <backup-path-or-s3-uri> <target-pgdata-dir>
#
# Examples:
#   pg_restore.sh /var/backups/eios/postgres/eios_pg_backup_20260622T120000Z /var/lib/postgresql/data
#   pg_restore.sh s3://eios-backups/postgres/eios_pg_backup_20260622T120000Z /var/lib/postgresql/data
#
# Steps:
#   1. Stop PostgreSQL
#   2. Clear target PGDATA
#   3. Restore backup (local tar or S3 download)
#   4. Write recovery.conf / recovery signal (PG12+)
#   5. Start PostgreSQL — it replays WAL and comes up read-write
#
# IMPORTANT: Review and test this script in a staging environment before use in production.

set -euo pipefail

BACKUP_SOURCE="${1:?Usage: pg_restore.sh <backup-source> <target-pgdata>}"
TARGET_PGDATA="${2:?Usage: pg_restore.sh <backup-source> <target-pgdata>}"

echo "[$(date -u +%FT%TZ)] EIOS pg_restore starting"
echo "  Source : ${BACKUP_SOURCE}"
echo "  Target : ${TARGET_PGDATA}"
echo ""
read -r -p "WARNING: This will OVERWRITE ${TARGET_PGDATA}. Type 'RESTORE' to confirm: " confirm
[[ "${confirm}" != "RESTORE" ]] && { echo "Aborted."; exit 1; }

# ── 1. Stop PostgreSQL ────────────────────────────────────────────────────────
echo "[$(date -u +%FT%TZ)] Stopping PostgreSQL..."
pg_ctlcluster stop 2>/dev/null || pg_ctl stop -D "${TARGET_PGDATA}" -m fast 2>/dev/null || true

# ── 2. Clear target PGDATA ───────────────────────────────────────────────────
echo "[$(date -u +%FT%TZ)] Clearing ${TARGET_PGDATA}..."
rm -rf "${TARGET_PGDATA:?}"
mkdir -p "${TARGET_PGDATA}"
chmod 700 "${TARGET_PGDATA}"

# ── 3. Restore backup ────────────────────────────────────────────────────────
if [[ "${BACKUP_SOURCE}" == s3://* ]]; then
  echo "[$(date -u +%FT%TZ)] Downloading from S3..."
  AWS_ARGS=()
  [[ -n "${S3_ENDPOINT_URL:-}" ]] && AWS_ARGS+=("--endpoint-url" "${S3_ENDPOINT_URL}")
  aws s3 cp "${BACKUP_SOURCE}/" "${TARGET_PGDATA}/" --recursive "${AWS_ARGS[@]}"
else
  echo "[$(date -u +%FT%TZ)] Restoring from local path..."
  if [[ -f "${BACKUP_SOURCE}/base.tar.gz" ]]; then
    tar -xzf "${BACKUP_SOURCE}/base.tar.gz" -C "${TARGET_PGDATA}"
  elif [[ -d "${BACKUP_SOURCE}" ]]; then
    cp -a "${BACKUP_SOURCE}/." "${TARGET_PGDATA}/"
  else
    echo "ERROR: Cannot determine backup format at ${BACKUP_SOURCE}" >&2; exit 1
  fi
fi

# ── 4. Write recovery signal (PostgreSQL 12+) ─────────────────────────────────
touch "${TARGET_PGDATA}/recovery.signal"
echo "[$(date -u +%FT%TZ)] recovery.signal written — PostgreSQL will enter recovery on start."

# ── 5. Fix permissions ───────────────────────────────────────────────────────
chown -R postgres:postgres "${TARGET_PGDATA}" 2>/dev/null || true
chmod 700 "${TARGET_PGDATA}"

echo ""
echo "[$(date -u +%FT%TZ)] Restore complete."
echo "  Start PostgreSQL manually and verify connectivity before updating application config."
echo "  After recovery: run 'SELECT pg_is_in_recovery();' — should return 'f' (false)."
