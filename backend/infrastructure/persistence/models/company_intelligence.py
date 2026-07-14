"""Company Intelligence — strukturierte Kennzahlen und Signale aus Dokumenten."""

from __future__ import annotations

from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base


class CompanyMetricModel(Base):
    __tablename__ = "company_metrics"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(sa.String, nullable=True, index=True)

    metric_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # financial: revenue, ebitda, ebitda_margin, net_income, employees, capex, free_cashflow, debt_ratio
    # esg:       co2_scope1, co2_scope2, co2_scope3, water_m3, energy_gwh, renewable_energy_pct,
    #            women_leadership_pct, supplier_audited_pct
    # cross:     esg_score, credit_rating, supplier_count

    value: Mapped[float] = mapped_column(sa.Numeric(20, 4), nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    # EUR, EUR_M, EUR_B, tCO2, tCO2_M, MWh, GWh, m3, PCT, COUNT

    year: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    period: Mapped[str] = mapped_column(sa.String(8), nullable=False, default="FY")
    # FY, Q1, Q2, Q3, Q4, H1, H2

    source_doc_id: Mapped[str | None] = mapped_column(
        sa.String, sa.ForeignKey("document_files.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="exact")
    # exact | estimated | calculated

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id", "company_name", "metric_type", "year", "period",
            name="uq_company_metric_year",
        ),
        sa.Index("ix_cm_org_company", "organization_id", "company_name"),
        sa.Index("ix_cm_metric_year", "metric_type", "year"),
    )


class CompanySignalModel(Base):
    __tablename__ = "company_signals"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(sa.String, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(sa.String, nullable=True, index=True)

    signal_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    # rating_change, esg_target_set, esg_target_missed, legal_action, ceo_change,
    # acquisition, recall, insolvency_risk, commitment, milestone_reached, ...

    dimension: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    # financial | esg | governance | supply_chain | regulatory | reputation

    direction: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="neutral")
    # positive | negative | neutral

    severity: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="medium")
    # critical | high | medium | low

    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    event_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    source_doc_id: Mapped[str | None] = mapped_column(
        sa.String, sa.ForeignKey("document_files.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=sa.func.now()
    )

    __table_args__ = (
        sa.Index("ix_cs_org_company", "organization_id", "company_name"),
        sa.Index("ix_cs_dimension", "organization_id", "dimension"),
        sa.Index("ix_cs_signal_type", "signal_type"),
        sa.Index("ix_cs_year", "organization_id", "year"),
    )
