"""M47 — Data Residency Audit Log ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DataResidencyAuditLogModel(Base):
    """Immutable audit log for data residency access events.

    Records every request where an organization's declared region
    differs from the serving instance's region (cross_region), or
    where residency metadata is missing (region_unknown).

    This table is append-only — no updates, no deletes.
    """

    __tablename__ = "data_residency_audit_log"
    __table_args__ = (
        Index("ix_draudit_org", "organization_id"),
        Index("ix_draudit_event_type", "event_type"),
        Index("ix_draudit_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    request_method: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    # Region declared on the organization's data_residency field
    org_region: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Region this EIOS instance is deployed in
    instance_region: Mapped[str] = mapped_column(String(10), nullable=False)
    # local_access | cross_region_access | region_unknown
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
