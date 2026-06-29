"""
EIOS ORM Models — Product Twin (M27 / KAN-98)

Two tables for the Product aggregate:
  products           — core product / SKU identity
  product_bom_items  — bill-of-materials links (product → material)

Compliance and sustainability are aggregated at the service layer
from linked material records — no extra stored model needed.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ProductModel(BaseModel):
    """Core product entity — identity, classification, physical properties."""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_prod_org", "organization_id"),
        Index("ix_prod_type", "product_type"),
        Index("ix_prod_status", "product_status"),
        Index("ix_prod_sku", "sku"),
        Index("ix_prod_gtin", "gtin"),
        Index("ix_prod_category", "category"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    product_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    # Commercial identifiers
    sku: Mapped[str | None] = mapped_column(String(200), nullable=True)
    internal_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gtin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Classification
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Physical / commercial
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False, default="pcs")
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    country_of_manufacture: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Regulatory scope
    is_regulated_product: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_market: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProductBOMItemModel(BaseModel):
    """Bill-of-materials item — one material that goes into a product."""

    __tablename__ = "product_bom_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "product_id", "material_id",
            name="uq_prod_bom_product_material",
        ),
        Index("ix_pbom_product", "product_id"),
        Index("ix_pbom_material", "material_id"),
        Index("ix_pbom_org", "organization_id"),
        Index("ix_pbom_concern", "is_substance_of_concern"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # Quantity
    weight_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Flags
    is_substance_of_concern: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
