from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ProcessModel(BaseModel):
    __tablename__ = "processes"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    process_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    steps: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    owner_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
