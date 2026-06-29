"""
M27 — Product Twin Domain (KAN-98)

Core entities for the Product aggregate:
  Product         — finished/semi-finished good, component or spare part
  ProductBOMItem  — bill-of-materials link (product → material)

Compliance and sustainability are aggregated at the service layer from
linked MaterialComplianceFlag and MaterialSustainabilityMetric records,
so no separate stored entity is needed in M3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ProductType(str, Enum):
    FINISHED_GOOD = "FINISHED_GOOD"
    SEMI_FINISHED = "SEMI_FINISHED"
    COMPONENT = "COMPONENT"
    SPARE_PART = "SPARE_PART"
    SERVICE = "SERVICE"
    OTHER = "OTHER"


class ProductStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"
    ARCHIVED = "ARCHIVED"


class TargetMarket(str, Enum):
    EU = "EU"
    US = "US"
    UK = "UK"
    CN = "CN"
    GLOBAL = "GLOBAL"
    OTHER = "OTHER"


@dataclass
class Product:
    id: str
    organization_id: str
    name: str
    product_type: ProductType
    product_status: ProductStatus
    # Commercial identifiers
    sku: str | None
    internal_code: str | None
    gtin: str | None                    # EAN / barcode
    # Classification
    category: str | None
    brand: str | None
    # Physical
    unit_of_measure: str
    weight_kg: float | None
    country_of_manufacture: str | None
    # Regulatory scope
    is_regulated_product: bool          # subject to DPP / labelling obligations
    target_market: TargetMarket | None
    # Free text
    description: str | None
    notes: str | None
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: str | None


@dataclass
class ProductBOMItem:
    """Bill-of-materials entry: one material that goes into a product."""

    id: str
    organization_id: str
    product_id: str
    material_id: str
    # Quantity fields (either weight_pct OR quantity+unit — both optional)
    weight_pct: float | None            # % by weight of this material in the product
    quantity: float | None              # absolute quantity
    unit: str | None
    # Flags
    is_substance_of_concern: bool       # e.g. SVHC listed
    # Notes
    notes: str | None
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: str | None
