"""Unit tests — Product Twin (M27 / KAN-102)

Uses MagicMock / AsyncMock — no real database or Kafka needed.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.product.service import ProductBOMService, ProductService
from domain.product import ProductStatus, ProductType, TargetMarket


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_kafka():
    kafka = MagicMock()
    kafka.publish_product_event = AsyncMock()
    return kafka


def _make_product_model(org_id: str, product_id: str | None = None):
    m = MagicMock()
    m.id = product_id or _uid()
    m.organization_id = org_id
    m.name = "Battery Pack B1"
    m.product_type = ProductType.FINISHED_GOOD.value
    m.product_status = ProductStatus.ACTIVE.value
    m.sku = "BP-B1-001"
    m.internal_code = "P-001"
    m.gtin = "4006381333931"
    m.category = "Energy Storage"
    m.brand = "EIOS"
    m.unit_of_measure = "pcs"
    m.weight_kg = 2.5
    m.country_of_manufacture = "DE"
    m.is_regulated_product = True
    m.target_market = TargetMarket.EU.value
    m.description = "18650 battery pack"
    m.notes = None
    m.status = "Draft"
    m.version = 1
    m.created_at = MagicMock()
    m.updated_at = MagicMock()
    return m


# ── ProductService ────────────────────────────────────────────────────────────

class TestProductService:
    @pytest.mark.asyncio
    async def test_create_product(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "application.product.service.ProductModel",
            return_value=_make_product_model(org_id),
        ):
            svc = ProductService(db, kafka)
            result = await svc.create(
                organization_id=org_id,
                name="Battery Pack B1",
                product_type=ProductType.FINISHED_GOOD,
                sku="BP-B1-001",
                is_regulated_product=True,
                target_market=TargetMarket.EU,
                actor_id=_uid(),
            )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        kafka.publish_product_event.assert_awaited_once()
        assert result.organization_id == org_id

    @pytest.mark.asyncio
    async def test_get_product_correct_org(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_product_model(org_id)
        db.get.return_value = model

        svc = ProductService(db, kafka)
        result = await svc.get(org_id, model.id)
        assert result is model

    @pytest.mark.asyncio
    async def test_get_product_wrong_org_returns_none(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_product_model(org_id)
        db.get.return_value = model

        svc = ProductService(db, kafka)
        result = await svc.get("other-org", model.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_product_not_found(self):
        db = _make_db()
        db.get.return_value = None
        kafka = _make_kafka()

        svc = ProductService(db, kafka)
        result = await svc.get("org", "missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_product(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_product_model(org_id)
        db.get.return_value = model

        svc = ProductService(db, kafka)
        result = await svc.update(
            org_id, model.id,
            name="Battery Pack B2",
            product_status=ProductStatus.ACTIVE,
            actor_id=_uid(),
        )

        assert result is model
        assert model.name == "Battery Pack B2"
        assert model.product_status == ProductStatus.ACTIVE.value
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_archive_product(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_product_model(org_id)
        db.get.return_value = model

        svc = ProductService(db, kafka)
        result = await svc.archive(org_id, model.id)

        assert result is True
        assert model.product_status == ProductStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_archive_product_not_found(self):
        db = _make_db()
        db.get.return_value = None
        kafka = _make_kafka()

        svc = ProductService(db, kafka)
        result = await svc.archive("org", "missing")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_products(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_product_model(org_id)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [model]
        db.execute = AsyncMock(side_effect=[count_result, list_result])

        svc = ProductService(db, kafka)
        items, total = await svc.list_for_org(org_id)

        assert total == 1
        assert len(items) == 1


# ── ProductBOMService ─────────────────────────────────────────────────────────

class TestProductBOMService:
    def _make_bom_item(self, org_id: str, product_id: str, material_id: str):
        m = MagicMock()
        m.id = _uid()
        m.organization_id = org_id
        m.product_id = product_id
        m.material_id = material_id
        m.weight_pct = 30.0
        m.quantity = None
        m.unit = None
        m.is_substance_of_concern = False
        m.notes = None
        m.status = "Draft"
        m.version = 1
        m.created_at = MagicMock()
        m.updated_at = MagicMock()
        return m

    @pytest.mark.asyncio
    async def test_add_bom_item_publishes_kafka(self):
        org_id = _uid()
        product_id = _uid()
        material_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        bom_model = self._make_bom_item(org_id, product_id, material_id)

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "application.product.service.ProductBOMItemModel",
            return_value=bom_model,
        ):
            svc = ProductBOMService(db, kafka)
            result = await svc.add_item(
                organization_id=org_id,
                product_id=product_id,
                material_id=material_id,
                weight_pct=30.0,
                is_substance_of_concern=False,
            )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        kafka.publish_product_event.assert_awaited_once()
        assert result.weight_pct == 30.0

    @pytest.mark.asyncio
    async def test_list_bom(self):
        org_id = _uid()
        product_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        item = self._make_bom_item(org_id, product_id, _uid())
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = [item]
        db.execute = AsyncMock(return_value=exec_result)

        svc = ProductBOMService(db, kafka)
        items = await svc.list_bom(org_id, product_id)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_delete_bom_item_not_found(self):
        db = _make_db()
        db.get.return_value = None
        kafka = _make_kafka()

        svc = ProductBOMService(db, kafka)
        result = await svc.delete_item("org", "missing")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_bom_item_wrong_org(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        item = MagicMock()
        item.organization_id = org_id
        db.get.return_value = item

        svc = ProductBOMService(db, kafka)
        result = await svc.delete_item("wrong-org", item.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_aggregate_compliance_empty_bom(self):
        db = _make_db()
        kafka = _make_kafka()

        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=exec_result)

        svc = ProductBOMService(db, kafka)
        result = await svc.aggregate_compliance("org", "product-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_aggregate_sustainability_empty_bom(self):
        db = _make_db()
        kafka = _make_kafka()

        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=exec_result)

        svc = ProductBOMService(db, kafka)
        result = await svc.aggregate_sustainability("org", "product-id")
        assert result == {"has_data": False}
