"""ORM Models — ERP Integration Layer (M6)

erp_connectors       — connector registry (SAP / Oracle / REST / CSV)
erp_sync_jobs        — per-run audit trail for inbound/outbound syncs
erp_field_mappings   — per-connector field translation rules (stored as JSON)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ERPConnectorModel(Base):
    """Registered ERP/PLM connector.

    Credentials are NEVER stored here — only a reference to a SecretReference ID.
    The adapter resolves the secret via the configured SecretProvider at runtime.
    """

    __tablename__ = "erp_connectors"
    __table_args__ = (
        Index("ix_erp_connectors_org", "organization_id"),
        Index("ix_erp_connectors_status", "connector_status"),
        UniqueConstraint("organization_id", "name", name="uq_erp_connectors_org_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Adapter type drives which client class is used
    adapter_type: Mapped[str] = mapped_column(String(30), nullable=False)  # SAP_ODATA | ORACLE_REST | REST | CSV
    # Connection target
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ID of a SecretReferenceModel row that holds the auth credentials
    secret_reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Auth scheme: BASIC | BEARER | OAUTH2 | NONE
    auth_scheme: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")
    # Lifecycle
    connector_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    # Optional cron expression for scheduled syncs (NULL = manual only)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Timeout for individual HTTP calls
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    # Optional extra config stored as JSON (page size, custom headers, etc.)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ERPSyncJobModel(Base):
    """Single execution of a connector sync (inbound or outbound)."""

    __tablename__ = "erp_sync_jobs"
    __table_args__ = (
        Index("ix_erp_sync_jobs_connector", "connector_id"),
        Index("ix_erp_sync_jobs_status", "job_status"),
        Index("ix_erp_sync_jobs_started", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # INBOUND = ERP → EIOS  |  OUTBOUND = EIOS → ERP
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # Entity type being synced: Material | Product | BOM | DPP
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    job_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Compact JSON array of per-record errors (first 100)
    error_details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runtime_seconds: Mapped[float | None] = mapped_column(String(20), nullable=True)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ERPFieldMappingModel(Base):
    """Field-level translation rules for a connector.

    Each row maps one ERP field path to one EIOS field path, with an
    optional transformation function name (trim, uppercase, date_iso, etc.).
    Stored one-row-per-field for queryability and UI editability.
    """

    __tablename__ = "erp_field_mappings"
    __table_args__ = (
        Index("ix_erp_field_mappings_connector", "connector_id"),
        UniqueConstraint(
            "connector_id", "entity_type", "erp_field",
            name="uq_erp_field_mapping_connector_entity_field",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    erp_field: Mapped[str] = mapped_column(String(300), nullable=False)
    eios_field: Mapped[str] = mapped_column(String(300), nullable=False)
    # Optional transform: trim | uppercase | lowercase | date_iso | float_parse | skip
    transform_fn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_required: Mapped[bool] = mapped_column(String(5), nullable=False, default=False)  # stored as "True"/"False"
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
