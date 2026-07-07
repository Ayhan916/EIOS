from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import BaseModel


class ApiKeyModel(BaseModel):
    __tablename__ = "api_keys"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    service_account_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requests_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_this_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minute_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requests_this_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hour_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
