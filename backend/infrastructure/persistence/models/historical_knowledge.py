from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class HistoricalKnowledgeModel(BaseModel):
    """Phase 4 — Historisches Lernen.

    Jeder Eintrag repräsentiert eine abgeschlossene Lernsequenz:
    Ereignis → Gegenmassnahme → Wirkung (Health-Delta).
    """

    __tablename__ = "historical_knowledge"
    __table_args__ = (
        sa.Index("ix_hk_org_right",    "organization_id", "csddd_right"),
        sa.Index("ix_hk_supplier_date", "supplier_id",    "reference_date"),
        sa.Index("ix_hk_source_event", "organization_id", "source_event_id"),
        sa.Index("ix_hk_source_cap",   "organization_id", "source_cap_id"),
    )

    organization_id: Mapped[str] = mapped_column(sa.String(36), nullable=False, index=True)
    supplier_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True, index=True)

    # Was ist passiert?
    event_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="")
    event_severity: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)

    # Was wurde unternommen?
    countermeasure_description: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    countermeasure_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="")

    # Was war das Ergebnis?
    outcome_description: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    outcome_category: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="unknown")
    health_delta: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

    # CSDDD-Bezug
    csddd_right: Mapped[str | None] = mapped_column(sa.String(50), nullable=True, index=True)
    twin_dimension: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    # Volltextinhalt + Embedding
    content_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)

    # Quellenreferenzen
    source_event_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True, index=True)
    source_finding_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True, index=True)
    source_cap_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True, index=True)

    # Zeitstempel des ursprünglichen Ereignisses
    reference_date: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
