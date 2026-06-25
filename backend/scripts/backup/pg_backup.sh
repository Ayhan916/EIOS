#!/usr/bin/env bash
# pg_backup.sh — EIOS PostgreSQL base backup (M45.3)
#
# Creates a pg_basebackup snapshot and optionally uploads it to S3/MinIO.
#
# Usage:
#   pg_backup.sh              — local backup only
#   pg_backup.sh --s3         — local backup + upload to S3, delete local copy on success
#
# Required env vars:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
#
# Optional env vars (S3 upload):
#   S3_BUCKET        (default: eios-backups)
#   S3_ENDPOINT_URL  (empty = AWS S3; set for MinIO)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#
# Exit codes:
#   0 — success
#   1 — backup failed
#   2 — S3 upload failed (local backup retained)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/eios/postgres}"
S3_BUCKET="${S3_BUCKET:-eios-backups}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_NAME="eios_pg_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
UPLOAD_TO_S3=false

for arg in "$@"; do
  [[ "$arg" == "--s3" ]] && UPLOAD_TO_S3=true
done

echo "[$(date -u +%FT%TZ)] EIOS pg_backup starting: ${BACKUP_NAME}"

mkdir -p "${BACKUP_DIR}"

# ── Base backup ───────────────────────────────────────────────────────────────
pg_basebackup \
  --host="${PGHOST:-localhost}" \
  --port="${PGPORT:-5432}" \
  --username="${PGUSER:-eios}" \
  --pgdata="${BACKUP_PATH}" \
  --format=tar \
  --gzip \
  --compress=9 \
  --checkpoint=fast \
  --wal-method=stream \
  --progress \
  --verbose

echo "[$(date -u +%FT%TZ)] Base backup complete: ${BACKUP_PATH}"

# Write a health marker so the Celery maintenance task can verify freshness
echo "${TIMESTAMP}" > "${BACKUP_DIR}/.last_backup_timestamp"

# ── Optional S3 upload ────────────────────────────────────────────────────────
if [[ "${UPLOAD_TO_S3}" == "true" ]]; then
  echo "[$(date -u +%FT%TZ)] Uploading to S3: s3://${S3_BUCKET}/postgres/${BACKUP_NAME}/"

  AWS_ARGS=()
  if [[ -n "${S3_ENDPOINT_URL:-}" ]]; then
    AWS_ARGS+=("--endpoint-url" "${S3_ENDPOINT_URL}")
  fi

  if aws s3 cp "${BACKUP_PATH}/" "s3://${S3_BUCKET}/postgres/${BACKUP_NAME}/" \
       --recursive --no-progress "${AWS_ARGS[@]}"; then

    # Also update the remote health marker
    echo "${TIMESTAMP}" | aws s3 cp - \
      "s3://${S3_BUCKET}/postgres/.last_backup_timestamp" \
      --content-type text/plain "${AWS_ARGS[@]}"

    echo "[$(date -u +%FT%TZ)] S3 upload complete. Removing local copy."
    rm -rf "${BACKUP_PATH}"
  else
    echo "[$(date -u +%FT%TZ)] ERROR: S3 upload failed. Local backup retained at ${BACKUP_PATH}" >&2
    exit 2
  fi
fi

echo "[$(date -u +%FT%TZ)] pg_backup finished successfully."
