"""SQLAlchemy models for Scoping Study (CSDDD Art. 8 Abs. 3)."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from infrastructure.persistence.models.base import Base


class ScopingConfigModel(Base):
    __tablename__ = "scoping_configs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    risk_score_threshold_p1 = Column(Float, nullable=False, default=7.0)
    risk_score_threshold_p2 = Column(Float, nullable=False, default=4.0)
    high_risk_countries = Column(Text, nullable=True)  # JSON list
    high_risk_sectors = Column(Text, nullable=True)  # JSON list
    revenue_threshold_pct = Column(Float, nullable=False, default=5.0)
    notes = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ScopingConfigAuditLogModel(Base):
    __tablename__ = "scoping_config_audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    config_id = Column(PG_UUID(as_uuid=True), nullable=False)
    action = Column(String(100), nullable=False)
    performed_by = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ScopingStudyModel(Base):
    __tablename__ = "scoping_studies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    report_year = Column(Integer, nullable=False)
    config_id = Column(PG_UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    results_snapshot = Column(Text, nullable=True)  # JSON list of ScopingResult dicts
    methodology_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)
    next_review_due = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
