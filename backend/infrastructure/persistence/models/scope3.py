"""M8 — Scope 3 Supply Chain Carbon Inventory ORM models.

Tables:
  product_carbon_footprints  — versioned PCF record per product computed from BOM × LCA
  scope3_inventories         — annual Scope 3 Cat. 1 aggregate across all product PCFs
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ProductCarbonFootprintModel(BaseModel):
    """Persistent, versioned Product Carbon Footprint (PCF) computed from BOM × LCA.

    formula: Σ (weight_pct_i / 100) × co2e_per_kg_i  for each BOM material i
    Deterministic: same BOM + same LCA data always produces the same result.
    """

    __tablename__ = "product_carbon_footprints"
    __table_args__ = (
        Index("ix_pcf_org", "organization_id"),
        Index("ix_pcf_product", "product_id"),
        Index("ix_pcf_year", "reporting_year"),
        Index("ix_pcf_result", "pcf_kg_co2e_per_unit"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Core PCF result
    pcf_kg_co2e_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    pcf_source: Mapped[str] = mapped_column(String(30), nullable=False, default="computed")
    # Coverage
    bom_materials_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bom_materials_with_lca: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weight_coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Breakdown: list of {material_id, material_name, weight_pct, co2e_per_kg, contribution_kg_co2e}
    material_breakdown: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Calculation metadata
    calc_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Scope3InventoryModel(BaseModel):
    """Annual Scope 3 Category 1 (Purchased Goods & Services) inventory.

    Aggregated from all ProductCarbonFootprintModel records for the org × year.
    One record per (organization_id, reporting_year). Refresh is idempotent —
    recalculating overwrites the existing record for that year.
    """

    __tablename__ = "scope3_inventories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "reporting_year",
            name="uq_scope3_inventory_org_year",
        ),
        Index("ix_scope3_inv_org", "organization_id"),
        Index("ix_scope3_inv_year", "reporting_year"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Totals
    total_pcf_kg_co2e: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_pcf_tco2e: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    products_included: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_with_full_lca: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_with_partial_lca: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_without_lca: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Top contributors: list of {product_id, pcf_kg_co2e}
    top_contributors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Calculation metadata
    calc_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
