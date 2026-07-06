"""SQLAlchemy models — Board Sign-off Trail (CSDDD Art. 22)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base


class BoardSignoffRequestModel(Base):
    __tablename__ = "board_signoff_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    signoff_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    decisions: Mapped[list[BoardDecisionModel]] = relationship(
        "BoardDecisionModel", back_populates="request", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_board_signoff_requests_org_status", "organization_id", "status"),
        Index("ix_board_signoff_requests_org_type", "organization_id", "signoff_type"),
    )


class BoardDecisionModel(Base):
    __tablename__ = "board_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("board_signoff_requests.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    decided_by_role: Mapped[str] = mapped_column(String(30), nullable=False, default="board_member")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[BoardSignoffRequestModel] = relationship(
        "BoardSignoffRequestModel", back_populates="decisions"
    )

    __table_args__ = (
        Index("ix_board_decisions_request", "request_id"),
    )
