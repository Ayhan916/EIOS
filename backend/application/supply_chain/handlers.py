"""Supply Chain Event Handlers — M5

Handlers registered with KafkaEventConsumer that implement cascade business logic:

1. material.compliance.flag_set
   → Find all active DPPs that include this material in their BOM
   → Trigger refresh_snapshot() on each (recompute non_compliant_regulations_count)

2. product.bom.item_added
   → Invalidate DPP snapshots for the product (mark for refresh via refresh_snapshot)

3. supplier.certification.expiring_soon
   → Write a notification record for the supplier's managing users

Event handlers receive (event_dict, kafka_partition, kafka_offset).
They share a SQLAlchemy session factory — each handler opens its own session
to avoid long-lived connections during slow consumer loops.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.dpp.service import DPPService
from infrastructure.kafka.consumer import KafkaEventConsumer
from infrastructure.kafka.events import MaterialEventType, ProductEventType, SupplierEventType
from infrastructure.kafka.producer import get_kafka_producer
from infrastructure.persistence.models.dpp import DigitalProductPassportModel
from infrastructure.persistence.models.product import ProductBOMItemModel
from shared.config import settings

logger = structlog.get_logger(__name__)


class SupplyChainHandlers:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # ── material.compliance.flag_set → refresh affected DPPs ─────────────────

    async def on_material_compliance_flag_set(
        self, event: dict, partition: int, offset: int
    ) -> None:
        payload = event.get("payload", {})
        material_id = payload.get("material_id")
        organization_id = event.get("organization_id")

        if not material_id or not organization_id:
            return

        async with self._session_factory() as session:
            # Find all products that contain this material in their BOM
            bom_stmt = select(ProductBOMItemModel.product_id).where(
                ProductBOMItemModel.organization_id == organization_id,
                ProductBOMItemModel.material_id == material_id,
            )
            bom_result = await session.execute(bom_stmt)
            product_ids = list({row[0] for row in bom_result.all()})

            if not product_ids:
                return

            # Find all active DPPs for those products
            dpp_stmt = select(DigitalProductPassportModel).where(
                DigitalProductPassportModel.organization_id == organization_id,
                DigitalProductPassportModel.product_id.in_(product_ids),
                DigitalProductPassportModel.dpp_status.in_(["DRAFT", "ACTIVE"]),
            )
            dpp_result = await session.execute(dpp_stmt)
            dpps = list(dpp_result.scalars().all())

            kafka = get_kafka_producer()
            svc = DPPService(session, kafka)

            for dpp in dpps:
                try:
                    await svc.refresh_snapshot(organization_id, dpp.id, actor_id="system")
                    await session.commit()
                    logger.info(
                        "dpp_refreshed_on_compliance_change",
                        dpp_id=dpp.id,
                        material_id=material_id,
                    )
                except Exception as exc:
                    await session.rollback()
                    logger.error(
                        "dpp_refresh_failed",
                        dpp_id=dpp.id,
                        material_id=material_id,
                        error=str(exc),
                    )

    # ── product.bom.item_added → refresh DPP snapshots for the product ────────

    async def on_bom_item_added(self, event: dict, partition: int, offset: int) -> None:
        payload = event.get("payload", {})
        product_id = payload.get("product_id")
        organization_id = event.get("organization_id")

        if not product_id or not organization_id:
            return

        async with self._session_factory() as session:
            dpp_stmt = select(DigitalProductPassportModel).where(
                DigitalProductPassportModel.organization_id == organization_id,
                DigitalProductPassportModel.product_id == product_id,
                DigitalProductPassportModel.dpp_status.in_(["DRAFT", "ACTIVE"]),
            )
            dpp_result = await session.execute(dpp_stmt)
            dpps = list(dpp_result.scalars().all())

            kafka = get_kafka_producer()
            svc = DPPService(session, kafka)

            for dpp in dpps:
                try:
                    await svc.refresh_snapshot(organization_id, dpp.id, actor_id="system")
                    await session.commit()
                    logger.info(
                        "dpp_refreshed_on_bom_change",
                        dpp_id=dpp.id,
                        product_id=product_id,
                    )
                except Exception as exc:
                    await session.rollback()
                    logger.error(
                        "dpp_refresh_failed_bom",
                        dpp_id=dpp.id,
                        product_id=product_id,
                        error=str(exc),
                    )

    # ── supplier.certification.expiring_soon → structured log + future notify ──

    async def on_certification_expiring_soon(
        self, event: dict, partition: int, offset: int
    ) -> None:
        """Log the expiry event. The event_log table records it for the UI.
        Targeted user notifications require a user_id lookup — wired in a
        future notification-dispatch service when user assignment is known."""
        payload = event.get("payload", {})
        supplier_id = payload.get("supplier_id")
        organization_id = event.get("organization_id")
        expiry_date = payload.get("expiry_date")

        logger.warning(
            "supplier_certification_expiring_soon",
            organization_id=organization_id,
            supplier_id=supplier_id,
            expiry_date=expiry_date,
            note="Recorded in event_log; targeted notification dispatch pending user-assignment feature",
        )

    def register_all(self, consumer: KafkaEventConsumer) -> None:
        """Wire all handlers to the consumer."""
        consumer.register(
            settings.kafka_material_topic,
            MaterialEventType.COMPLIANCE_FLAG_SET.value,
            self.on_material_compliance_flag_set,
        )
        consumer.register(
            settings.kafka_product_topic,
            ProductEventType.BOM_ITEM_ADDED.value,
            self.on_bom_item_added,
        )
        consumer.register(
            settings.kafka_supplier_topic,
            SupplierEventType.CERTIFICATION_EXPIRING_SOON.value,
            self.on_certification_expiring_soon,
        )
