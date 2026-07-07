"""M45.2 — S3 object storage + Celery async ingestion columns.

Changes:
  1. evidences.s3_object_key    VARCHAR(1000) nullable — S3 key for the uploaded file
  2. evidences.ingestion_job_id VARCHAR(36)   nullable — Celery task ID for polling

When S3 is disabled (S3_ENABLED=false, the default), s3_object_key remains NULL
and ingestion runs synchronously as before.  These columns are additive.

Revision ID: 055
Revises: 054
Create Date: 2026-06-22
"""

import sqlalchemy as sa

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidences",
        sa.Column("s3_object_key", sa.String(1000), nullable=True),
    )
    op.add_column(
        "evidences",
        sa.Column("ingestion_job_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidences", "ingestion_job_id")
    op.drop_column("evidences", "s3_object_key")
