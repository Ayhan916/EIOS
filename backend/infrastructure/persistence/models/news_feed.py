from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class NewsArticleModel(Base):
    __tablename__ = "news_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    translated_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False, default="supplier")
    match_query: Mapped[str | None] = mapped_column(String(500), nullable=True)


class NewsSupplierAssignmentModel(Base):
    __tablename__ = "news_supplier_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    match_reason: Mapped[str] = mapped_column(String(20), nullable=False)
