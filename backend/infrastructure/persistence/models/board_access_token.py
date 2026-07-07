"""M48.2 G-034 — Board Portal Access Tokens (time-limited read-only)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BoardAccessTokenModel(Base):
    """A scoped, time-limited read-only JWT for Board Portal share-links.

    Security invariants:
    - No refresh token — access expires after expires_at.
    - Scope limited to the report_id that created it.
    - revoked=True immediately invalidates the token.
    - token_hash stores SHA-256(token) — raw JWT is never persisted.
    """

    __tablename__ = "board_access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    # Which sections of the report are accessible
    allowed_sections: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    # Optional: email of the person the link was shared with (for audit trail)
    shared_with_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_count: Mapped[int] = mapped_column(nullable=False, default=0)
