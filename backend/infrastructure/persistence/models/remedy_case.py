"""SQLAlchemy models for Remedy Case Manager (CSDDD Art. 12)."""

from sqlalchemy import (
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


class RemedyCaseModel(Base):
    __tablename__ = "remedy_cases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    incident_date = Column(DateTime(timezone=True), nullable=False)
    affected_count = Column(Integer, nullable=False, default=0)
    affected_type = Column(String(50), nullable=False)
    rights = Column(Text, nullable=True)  # JSON list
    remedy_types = Column(Text, nullable=True)  # JSON list
    severity_score = Column(Float, nullable=False, default=0.0)
    impact_causation = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="open")
    source_grievance_id = Column(PG_UUID(as_uuid=True), nullable=True)
    co_responsible_parties = Column(Text, nullable=True)  # JSON list
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by = Column(String(255), nullable=True)
    closure_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RemedyBeneficiaryModel(Base):
    __tablename__ = "remedy_beneficiaries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    remedy_case_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("remedy_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference = Column(String(255), nullable=False)
    affected_type = Column(String(50), nullable=False)
    promised_compensation = Column(Float, nullable=True)
    received_compensation = Column(Float, nullable=True)
    confirmation_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RemedyActionModel(Base):
    __tablename__ = "remedy_actions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    remedy_case_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("remedy_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="todo")
    responsible_party = Column(String(255), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RemedyAuditLogModel(Base):
    __tablename__ = "remedy_audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    remedy_case_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("remedy_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(100), nullable=False)
    performed_by = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
