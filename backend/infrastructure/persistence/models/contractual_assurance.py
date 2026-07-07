"""SQLAlchemy persistence models — Contractual Assurance (CSDDD Art. 10)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base


class ContractClauseModel(Base):
    __tablename__ = "contract_clauses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    cascade_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assurances: Mapped[list[ContractAssuranceModel]] = relationship(
        "ContractAssuranceModel", back_populates="clause", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_contract_clauses_org_category", "organization_id", "category"),)


class ContractAssuranceModel(Base):
    __tablename__ = "contract_assurances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    clause_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_clauses.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cascade_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cascade_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    clause: Mapped[ContractClauseModel] = relationship(
        "ContractClauseModel", back_populates="assurances"
    )
    audit_logs: Mapped[list[ClauseAuditLogModel]] = relationship(
        "ClauseAuditLogModel", back_populates="assurance", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_contract_assurances_supplier_clause", "supplier_id", "clause_id"),
        Index("ix_contract_assurances_org_status", "organization_id", "status"),
    )


class ClauseAuditLogModel(Base):
    __tablename__ = "clause_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    assurance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_assurances.id", ondelete="CASCADE"), nullable=False
    )
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assurance: Mapped[ContractAssuranceModel] = relationship(
        "ContractAssuranceModel", back_populates="audit_logs"
    )
