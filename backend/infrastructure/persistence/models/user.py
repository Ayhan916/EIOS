from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_preferences: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "email_workflow_completed": True,
            "email_action_overdue": True,
            "email_assessment_approved": True,
            "email_recommendation_assigned": True,
        },
    )

    # M40 — Enterprise RBAC scope fields (all nullable for backward compat)
    # enterprise_admin | bu_admin | regional_admin | None (org-scoped)
    enterprise_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enterprise_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    business_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    region_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    organization: Mapped[OrganizationModel | None] = relationship(back_populates="users")
