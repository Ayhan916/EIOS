"""SQLAlchemy models for CSDDD-002 DD-Governance (Art. 7)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class DDPolicyModel(BaseModel):
    __tablename__ = "dd_policies"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approved_role: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class CodeOfConductModel(BaseModel):
    __tablename__ = "codes_of_conduct"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    coc_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    acceptance_validity_months: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=24
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    linked_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class CoCAcceptanceModel(BaseModel):
    __tablename__ = "coc_acceptances"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    coc_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    coc_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    ip_hash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
