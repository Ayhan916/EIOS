"""Supplier Digital Twin ORM Models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class SupplierDigitalTwinModel(BaseModel):
    """Current intelligence state of a Supplier Digital Twin (one per supplier per org)."""

    __tablename__ = "supplier_digital_twins"
    __table_args__ = (
        UniqueConstraint("supplier_id", "organization_id", name="uq_twin_supplier_org"),
        Index("ix_twin_supplier_id", "supplier_id"),
        Index("ix_twin_org_id", "organization_id"),
        Index("ix_twin_overall_health", "overall_health"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Health dimensions (0–100, 100 = perfect)
    esg_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    compliance_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    financial_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    geopolitical_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    cyber_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    human_rights_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    environmental_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    operational_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)

    overall_health: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    health_trend: Mapped[str] = mapped_column(String(20), nullable=False, default="STABLE")
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    open_recommendations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    twin_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class IntelligenceTimelineEventModel(BaseModel):
    """Append-only intelligence timeline event for a supplier."""

    __tablename__ = "intelligence_timeline_events"
    __table_args__ = (
        Index("ix_ite_supplier_id", "supplier_id"),
        Index("ix_ite_org_id", "organization_id"),
        Index("ix_ite_occurred_at", "occurred_at"),
        Index("ix_ite_severity", "severity"),
        Index("ix_ite_event_category", "event_category"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    why_important: Mapped[str] = mapped_column(Text, nullable=False, default="")
    regulatory_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False, default="")

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    source_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    regulation_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risk_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    signal_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")

    twin_dimension_affected: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    health_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
