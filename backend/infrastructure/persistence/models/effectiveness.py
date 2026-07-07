"""SQLAlchemy models for Effectiveness Monitoring (CSDDD Art. 15)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from infrastructure.persistence.models.base import Base


class EffectivenessIndicatorModel(Base):
    __tablename__ = "effectiveness_indicators"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)  # NULL = global seed
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    indicator_type = Column(String(50), nullable=False)
    unit = Column(String(100), nullable=False, default="")
    data_source = Column(String(50), nullable=False, default="manual")
    csddd_article = Column(String(50), nullable=False, default="")
    risk_category = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EffectivenessReviewModel(Base):
    __tablename__ = "effectiveness_reviews"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    overall_rating = Column(Integer, nullable=True)
    key_findings = Column(Text, nullable=True)
    improvement_actions = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    submitted_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewLineModel(Base):
    __tablename__ = "review_lines"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    review_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("effectiveness_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    indicator_id = Column(PG_UUID(as_uuid=True), nullable=False)
    indicator_name = Column(String(255), nullable=False)
    measured_value = Column(Float, nullable=True)
    measured_text = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    auto_populated = Column(Boolean, nullable=False, default=False)
