from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.webhook_delivery import WebhookDelivery
from domain.webhook_subscription import WebhookSubscription
from infrastructure.persistence.models.webhook import WebhookDeliveryModel, WebhookSubscriptionModel
from infrastructure.persistence.repositories.base import BaseRepository
from shared.encryption import decrypt_field, encrypt_field


class SQLWebhookSubscriptionRepository(
    BaseRepository[WebhookSubscription, WebhookSubscriptionModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WebhookSubscriptionModel)

    def _to_model(self, entity: WebhookSubscription) -> WebhookSubscriptionModel:
        return WebhookSubscriptionModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            name=entity.name,
            target_url=entity.target_url,
            secret=encrypt_field(entity.secret),  # encrypt at rest
            events=entity.events,
            is_active=entity.is_active,
            failure_count=entity.failure_count,
            last_triggered_at=entity.last_triggered_at,
        )

    def _to_domain(self, model: WebhookSubscriptionModel) -> WebhookSubscription:
        return WebhookSubscription(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            name=model.name,
            target_url=model.target_url,
            secret=decrypt_field(model.secret),  # decrypt for application use
            events=list(model.events or []),
            is_active=model.is_active,
            failure_count=model.failure_count,
            last_triggered_at=model.last_triggered_at,
        )

    async def list_active_for_event(
        self, organization_id: str, event_type: str
    ) -> list[WebhookSubscription]:
        rows = (
            (
                await self._session.execute(
                    select(WebhookSubscriptionModel).where(
                        WebhookSubscriptionModel.organization_id == organization_id,
                        WebhookSubscriptionModel.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows if event_type in (r.events or [])]

    async def list_for_org(self, organization_id: str) -> list[WebhookSubscription]:
        rows = (
            (
                await self._session.execute(
                    select(WebhookSubscriptionModel)
                    .where(WebhookSubscriptionModel.organization_id == organization_id)
                    .order_by(WebhookSubscriptionModel.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]


class SQLWebhookDeliveryRepository(BaseRepository[WebhookDelivery, WebhookDeliveryModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WebhookDeliveryModel)

    def _to_model(self, entity: WebhookDelivery) -> WebhookDeliveryModel:
        return WebhookDeliveryModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            subscription_id=entity.subscription_id,
            event_type=entity.event_type,
            payload_hash=entity.payload_hash,
            payload=entity.payload,
            delivery_status=entity.delivery_status,
            response_code=entity.response_code,
            duration_ms=entity.duration_ms,
            retry_count=entity.retry_count,
            retry_at=entity.retry_at,
            error_message=entity.error_message,
            delivered_at=entity.delivered_at,
        )

    def _to_domain(self, model: WebhookDeliveryModel) -> WebhookDelivery:
        return WebhookDelivery(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            subscription_id=model.subscription_id,
            event_type=model.event_type,
            payload_hash=model.payload_hash,
            payload=model.payload,
            delivery_status=model.delivery_status,
            response_code=model.response_code,
            duration_ms=model.duration_ms,
            retry_count=model.retry_count,
            retry_at=model.retry_at,
            error_message=model.error_message,
            delivered_at=model.delivered_at,
        )

    async def list_for_subscription(
        self, subscription_id: str, limit: int = 50
    ) -> list[WebhookDelivery]:
        rows = (
            (
                await self._session.execute(
                    select(WebhookDeliveryModel)
                    .where(WebhookDeliveryModel.subscription_id == subscription_id)
                    .order_by(WebhookDeliveryModel.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def list_pending_retries(self, before: datetime) -> list[WebhookDelivery]:
        rows = (
            (
                await self._session.execute(
                    select(WebhookDeliveryModel).where(
                        WebhookDeliveryModel.delivery_status == "failed",
                        WebhookDeliveryModel.retry_at <= before,
                        WebhookDeliveryModel.retry_count < 5,
                    )
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]

    async def count_by_status_for_org(self, organization_id: str) -> dict[str, int]:
        """Return delivery counts grouped by status for all subscriptions in an org."""
        sub_ids = (
            (
                await self._session.execute(
                    select(WebhookSubscriptionModel.id).where(
                        WebhookSubscriptionModel.organization_id == organization_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if not sub_ids:
            return {"pending": 0, "failed": 0, "dead_letter": 0, "delivered": 0}
        rows = (
            await self._session.execute(
                select(
                    WebhookDeliveryModel.delivery_status,
                    func.count(WebhookDeliveryModel.id).label("cnt"),
                )
                .where(WebhookDeliveryModel.subscription_id.in_(sub_ids))
                .group_by(WebhookDeliveryModel.delivery_status)
            )
        ).all()
        counts: dict[str, int] = {"pending": 0, "failed": 0, "dead_letter": 0, "delivered": 0}
        for row in rows:
            counts[row.delivery_status] = row.cnt
        return counts

    async def list_for_org(self, organization_id: str, limit: int = 100) -> list[WebhookDelivery]:
        """Fetch deliveries for all subscriptions in an org (for delivery log UI)."""
        sub_ids = (
            (
                await self._session.execute(
                    select(WebhookSubscriptionModel.id).where(
                        WebhookSubscriptionModel.organization_id == organization_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if not sub_ids:
            return []
        rows = (
            (
                await self._session.execute(
                    select(WebhookDeliveryModel)
                    .where(WebhookDeliveryModel.subscription_id.in_(sub_ids))
                    .order_by(WebhookDeliveryModel.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [self._to_domain(r) for r in rows]
