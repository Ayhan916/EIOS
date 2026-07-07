"""Unit tests for M27 Supplier domain entity and enums."""

from __future__ import annotations

from domain.enums import SupplierStatus, SupplierTier
from domain.supplier import Supplier


class TestSupplierTier:
    def test_all_tiers_defined(self) -> None:
        assert SupplierTier.TIER_1.value == "Tier 1"
        assert SupplierTier.TIER_2.value == "Tier 2"
        assert SupplierTier.TIER_3.value == "Tier 3"
        assert SupplierTier.OTHER.value == "Other"

    def test_tier_is_str_enum(self) -> None:
        assert isinstance(SupplierTier.TIER_1, str)


class TestSupplierStatus:
    def test_status_values(self) -> None:
        assert SupplierStatus.ACTIVE.value == "Active"
        assert SupplierStatus.INACTIVE.value == "Inactive"


class TestSupplierEntity:
    def test_create_minimal(self) -> None:
        s = Supplier(organization_id="org-1", name="ACME Corp")
        assert s.name == "ACME Corp"
        assert s.organization_id == "org-1"
        assert s.supplier_tier == SupplierTier.TIER_1
        assert s.supplier_status == SupplierStatus.ACTIVE
        assert s.id is not None

    def test_create_full(self) -> None:
        s = Supplier(
            organization_id="org-2",
            name="Green Steel GmbH",
            legal_name="Green Steel GmbH & Co. KG",
            country="DE",
            industry="Steel Manufacturing",
            nace_code="C24.10",
            website="https://greensteel.de",
            supplier_tier=SupplierTier.TIER_2,
            supplier_status=SupplierStatus.INACTIVE,
            notes="Under compliance review",
        )
        assert s.legal_name == "Green Steel GmbH & Co. KG"
        assert s.nace_code == "C24.10"
        assert s.supplier_tier == SupplierTier.TIER_2
        assert s.supplier_status == SupplierStatus.INACTIVE

    def test_unique_ids(self) -> None:
        s1 = Supplier(organization_id="org-1", name="A")
        s2 = Supplier(organization_id="org-1", name="B")
        assert s1.id != s2.id

    def test_optional_fields_default_none(self) -> None:
        s = Supplier(organization_id="org-1", name="Minimal")
        assert s.legal_name is None
        assert s.nace_code is None
        assert s.website is None
        assert s.notes is None
