"""M47.1 — Control Framework Mapping model (G-028)."""

from __future__ import annotations

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ControlFrameworkMappingModel(Base):
    """Maps an EIOS control to an external framework control.

    Supports: ISO14001 | SOC2 | ISO27001 | GRC (and any custom string).
    One EIOS control may map to many framework controls across multiple frameworks.
    """

    __tablename__ = "control_framework_mappings"
    __table_args__ = (
        UniqueConstraint(
            "control_id", "framework_code", "framework_control_id",
            name="uq_ctrl_fw_mapping",
        ),
        Index("ix_ctrl_fw_control_id", "control_id"),
        Index("ix_ctrl_fw_code", "framework_code"),
        Index("ix_ctrl_fw_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    control_id: Mapped[str] = mapped_column(String(36), nullable=False)
    framework_code: Mapped[str] = mapped_column(String(30), nullable=False)
    # e.g. "ISO27001:A.8.1", "SOC2:CC6.1", "ISO14001:6.1.2"
    framework_control_id: Mapped[str] = mapped_column(String(100), nullable=False)
    framework_control_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # direct | partial | compensating
    mapping_type: Mapped[str] = mapped_column(String(20), nullable=False, default="direct")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
