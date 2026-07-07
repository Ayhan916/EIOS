"""M45 MFA Backup Codes.

One-time use codes issued during MFA setup. BCrypt-hashed at rest.
Each code may only be used once; used_at is set on consumption.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MFABackupCodeModel(Base):
    __tablename__ = "mfa_backup_codes"
    __table_args__ = (Index("ix_mfa_backup_codes_user_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
