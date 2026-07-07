"""M46.2 — Enterprise Data Layer.

New tables:
  ghg_emission_factors   — DEFRA 2023 + EPA 2023 standard emission factors (seeded)
  ghg_calculations       — per-activity GHG calculation records (audit trail)
  evidence_versions      — document version history linked to evidence

Revision ID: 056
Revises: 055
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None

# ── DEFRA 2023 and EPA 2023 emission factors ────────────────────────────────
# Sources:
#   DEFRA: "Greenhouse gas reporting: conversion factors 2023" (UK)
#   EPA:   "Emission Factors for Greenhouse Gas Inventories" (March 2023, US)
#
# Units: kgCO2e per stated unit
_FACTORS = [
    # ── DEFRA 2023 ─────────────────────────────────────────────────────────
    # Scope 1 — Fuel combustion
    (
        "SCOPE1",
        "fuel_combustion",
        "natural_gas",
        "kWh",
        0.18293,
        "DEFRA_2023",
        "UK",
        "Natural gas — net CV, kgCO2e/kWh",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "diesel",
        "litre",
        2.51320,
        "DEFRA_2023",
        "UK",
        "Diesel — kgCO2e/litre",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "petrol",
        "litre",
        2.16800,
        "DEFRA_2023",
        "UK",
        "Petrol — kgCO2e/litre",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "lpg",
        "litre",
        1.55540,
        "DEFRA_2023",
        "UK",
        "LPG — kgCO2e/litre",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "coal",
        "tonne",
        2228.00000,
        "DEFRA_2023",
        "UK",
        "Industrial coal — kgCO2e/tonne",
    ),
    # Scope 2 — Purchased electricity
    (
        "SCOPE2",
        "purchased_electricity",
        "electricity",
        "kWh",
        0.20707,
        "DEFRA_2023",
        "UK",
        "UK grid average electricity — kgCO2e/kWh (2023)",
    ),
    # Scope 3 — Business travel (per km, per passenger)
    (
        "SCOPE3",
        "business_travel",
        "car_petrol_small",
        "km",
        0.14519,
        "DEFRA_2023",
        "UK",
        "Car — petrol, small, kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "car_petrol_medium",
        "km",
        0.16844,
        "DEFRA_2023",
        "UK",
        "Car — petrol, medium, kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "car_diesel_medium",
        "km",
        0.16352,
        "DEFRA_2023",
        "UK",
        "Car — diesel, medium, kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "car_electric",
        "km",
        0.05290,
        "DEFRA_2023",
        "UK",
        "Car — battery electric vehicle, kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "rail_national",
        "km",
        0.03549,
        "DEFRA_2023",
        "UK",
        "Rail — national, kgCO2e/km per passenger",
    ),
    (
        "SCOPE3",
        "business_travel",
        "rail_international",
        "km",
        0.00641,
        "DEFRA_2023",
        "UK",
        "Rail — international (Eurostar), kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "flight_domestic",
        "km",
        0.24500,
        "DEFRA_2023",
        "UK",
        "Flights — domestic (with RFI), kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "flight_short_haul",
        "km",
        0.15259,
        "DEFRA_2023",
        "UK",
        "Flights — short haul economy (with RFI), kgCO2e/km",
    ),
    (
        "SCOPE3",
        "business_travel",
        "flight_long_haul",
        "km",
        0.19560,
        "DEFRA_2023",
        "UK",
        "Flights — long haul economy (with RFI), kgCO2e/km",
    ),
    # Scope 3 — Freight transport
    (
        "SCOPE3",
        "freight_transport",
        "road_hgv_avg",
        "tonne_km",
        0.07390,
        "DEFRA_2023",
        "UK",
        "Road freight — HGV average, kgCO2e/tonne.km",
    ),
    (
        "SCOPE3",
        "freight_transport",
        "air_freight",
        "tonne_km",
        1.12000,
        "DEFRA_2023",
        "UK",
        "Air freight, kgCO2e/tonne.km",
    ),
    (
        "SCOPE3",
        "freight_transport",
        "sea_freight",
        "tonne_km",
        0.01196,
        "DEFRA_2023",
        "UK",
        "Sea freight — bulk carrier avg, kgCO2e/tonne.km",
    ),
    (
        "SCOPE3",
        "freight_transport",
        "rail_freight",
        "tonne_km",
        0.02800,
        "DEFRA_2023",
        "UK",
        "Rail freight, kgCO2e/tonne.km",
    ),
    # Scope 3 — Purchased goods (spend-based, EEIO)
    (
        "SCOPE3",
        "purchased_goods",
        "spend_based",
        "GBP",
        0.41000,
        "DEFRA_2023",
        "UK",
        "Spend-based: average goods/services, kgCO2e/GBP",
    ),
    # ── EPA 2023 ────────────────────────────────────────────────────────────
    # Scope 1 — Fuel combustion
    (
        "SCOPE1",
        "fuel_combustion",
        "natural_gas",
        "therm",
        5.49000,
        "EPA_2023",
        "US",
        "Natural gas — kgCO2e/therm",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "diesel",
        "gallon",
        10.21000,
        "EPA_2023",
        "US",
        "Diesel (distillate fuel) — kgCO2e/US gallon",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "petrol",
        "gallon",
        8.78000,
        "EPA_2023",
        "US",
        "Motor gasoline — kgCO2e/US gallon",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "lpg",
        "gallon",
        5.68000,
        "EPA_2023",
        "US",
        "LPG — kgCO2e/US gallon",
    ),
    (
        "SCOPE1",
        "fuel_combustion",
        "coal_bituminous",
        "short_ton",
        2249.00000,
        "EPA_2023",
        "US",
        "Bituminous coal — kgCO2e/short ton",
    ),
    # Scope 2 — Purchased electricity
    (
        "SCOPE2",
        "purchased_electricity",
        "electricity",
        "kWh",
        0.38600,
        "EPA_2023",
        "US",
        "US national average electricity — kgCO2e/kWh (2023 eGRID)",
    ),
    (
        "SCOPE2",
        "purchased_electricity",
        "electricity_ca",
        "kWh",
        0.20600,
        "EPA_2023",
        "US",
        "US California grid electricity — kgCO2e/kWh (2023)",
    ),
    (
        "SCOPE2",
        "purchased_electricity",
        "electricity_tx",
        "kWh",
        0.39800,
        "EPA_2023",
        "US",
        "US Texas (ERCOT) electricity — kgCO2e/kWh (2023)",
    ),
    # Scope 3 — Business travel
    (
        "SCOPE3",
        "business_travel",
        "car_average",
        "mile",
        0.27600,
        "EPA_2023",
        "US",
        "Average passenger car — kgCO2e/mile",
    ),
    (
        "SCOPE3",
        "business_travel",
        "flight_domestic",
        "mile",
        0.16400,
        "EPA_2023",
        "US",
        "Air travel — domestic, economy, kgCO2e/passenger.mile",
    ),
    (
        "SCOPE3",
        "business_travel",
        "flight_long_haul",
        "mile",
        0.18300,
        "EPA_2023",
        "US",
        "Air travel — long haul, economy, kgCO2e/passenger.mile",
    ),
    # Scope 3 — Freight transport
    (
        "SCOPE3",
        "freight_transport",
        "road_truck_avg",
        "ton_mile",
        0.16100,
        "EPA_2023",
        "US",
        "Road freight — medium/heavy truck, kgCO2e/ton.mile",
    ),
    (
        "SCOPE3",
        "freight_transport",
        "rail_freight",
        "ton_mile",
        0.02200,
        "EPA_2023",
        "US",
        "Rail freight — kgCO2e/ton.mile",
    ),
    (
        "SCOPE3",
        "freight_transport",
        "air_freight",
        "ton_mile",
        1.86500,
        "EPA_2023",
        "US",
        "Air freight — kgCO2e/ton.mile",
    ),
    # Scope 3 — Purchased goods (spend-based)
    (
        "SCOPE3",
        "purchased_goods",
        "spend_based",
        "USD",
        0.55000,
        "EPA_2023",
        "US",
        "Spend-based: average goods/services, kgCO2e/USD",
    ),
]


def upgrade() -> None:
    # ── ghg_emission_factors ─────────────────────────────────────────────────
    op.create_table(
        "ghg_emission_factors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("factor_kgco2e_per_unit", sa.Float, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("year", sa.Integer, nullable=False, server_default="2023"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_custom", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ghg_factors_scope_cat", "ghg_emission_factors", ["scope", "category"])
    op.create_index("ix_ghg_factors_source", "ghg_emission_factors", ["source", "region"])

    # ── ghg_calculations ─────────────────────────────────────────────────────
    op.create_table(
        "ghg_calculations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column(
            "factor_id", sa.String(36), sa.ForeignKey("ghg_emission_factors.id"), nullable=False
        ),
        sa.Column("factor_kgco2e_per_unit", sa.Float, nullable=False),
        sa.Column("result_kgco2e", sa.Float, nullable=False),
        sa.Column("result_tco2e", sa.Float, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("reporting_year", sa.Integer, nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ghg_calc_org", "ghg_calculations", ["organization_id"])
    op.create_index("ix_ghg_calc_supplier", "ghg_calculations", ["supplier_id"])
    op.create_index("ix_ghg_calc_scope", "ghg_calculations", ["scope"])

    # ── evidence_versions ────────────────────────────────────────────────────
    op.create_table(
        "evidence_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidences.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("s3_key", sa.String(1000), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("file_mime_type", sa.String(200), nullable=True),
        sa.Column("ingestion_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.UniqueConstraint("evidence_id", "version_number", name="uq_evidence_version"),
    )
    op.create_index("ix_evidence_versions_evidence", "evidence_versions", ["evidence_id"])

    # ── Seed standard emission factors ───────────────────────────────────────
    now = datetime.now(UTC)
    conn = op.get_bind()
    for scope, category, subcategory, unit, factor, source, region, description in _FACTORS:
        conn.execute(
            sa.text(
                "INSERT INTO ghg_emission_factors "
                "(id, scope, category, subcategory, unit, factor_kgco2e_per_unit, source, region, year, description, is_custom, organization_id, created_at) "
                "VALUES (:id, :scope, :category, :subcategory, :unit, :factor, :source, :region, 2023, :desc, false, NULL, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "scope": scope,
                "category": category,
                "subcategory": subcategory,
                "unit": unit,
                "factor": factor,
                "source": source,
                "region": region,
                "desc": description,
                "now": now,
            },
        )


def downgrade() -> None:
    op.drop_table("evidence_versions")
    op.drop_table("ghg_calculations")
    op.drop_table("ghg_emission_factors")
