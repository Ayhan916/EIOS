"""
M30.1 Unit Tests — Webhook Recovery Worker

Tests for the recovery worker logic without real I/O.
All DB operations are mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.enums import EntityStatus, WebhookDeliveryStatus
from domain.webhook_delivery import WebhookDelivery
from domain.webhook_subscription import WebhookSubscription

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_delivery(
    *,
    delivery_id: str = "del-001",
    subscription_id: str = "sub-001",
    event_type: str = "assessment.completed",
    retry_count: int = 1,
    payload: dict | None = None,
) -> WebhookDelivery:
    return WebhookDelivery(
        id=delivery_id,
        subscription_id=subscription_id,
        event_type=event_type,
        payload_hash="abc123",
        payload=payload,
        delivery_status="failed",
        retry_count=retry_count,
        retry_at=datetime.now(UTC),
        status=EntityStatus.ACTIVE,
    )


def _make_subscription(
    *,
    sub_id: str = "sub-001",
    target_url: str = "https://example.com/hook",
    secret: str = "s3cr3t",
    is_active: bool = True,
) -> WebhookSubscription:
    return WebhookSubscription(
        id=sub_id,
        organization_id="org-001",
        name="Test Hook",
        target_url=target_url,
        secret=secret,
        events=["assessment.completed"],
        is_active=is_active,
        status=EntityStatus.ACTIVE,
    )


def _make_session_ctx(delivery_repo=None, sub_repo=None):
    """Build a mock AsyncSessionFactory() context manager chain.

    async with AsyncSessionFactory() as session, session.begin():
        ...
    """
    begin_ctx = MagicMock()
    begin_ctx.__aenter__ = AsyncMock(return_value=None)
    begin_ctx.__aexit__ = AsyncMock(return_value=False)

    db_session = MagicMock()
    db_session.begin = MagicMock(return_value=begin_ctx)

    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=db_session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)

    # AsyncSessionFactory() returns session_ctx
    factory = MagicMock(return_value=session_ctx)
    return factory


# ── _recover_pending tests ────────────────────────────────────────────────────


class TestRecoverPending:
    """Test _recover_pending filtering logic using mocked DB access."""

    def _build_mocks(self, deliveries, subscriptions_by_id):
        mock_delivery_repo = MagicMock()
        mock_delivery_repo.list_pending_retries = AsyncMock(return_value=deliveries)

        mock_sub_repo = MagicMock()
        mock_sub_repo.get_by_id = AsyncMock(side_effect=lambda sid: subscriptions_by_id.get(sid))

        mock_factory = _make_session_ctx()

        return mock_factory, mock_delivery_repo, mock_sub_repo

    @pytest.mark.asyncio
    async def test_no_deliveries_fires_no_tasks(self) -> None:
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks([], {})

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_delivery_without_payload_is_skipped(self) -> None:
        delivery = _make_delivery(payload=None)
        sub = _make_subscription()
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks(
            [delivery], {"sub-001": sub}
        )

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_inactive_subscription_skips_delivery(self) -> None:
        delivery = _make_delivery(payload={"event": "test"})
        sub = _make_subscription(is_active=False)
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks(
            [delivery], {"sub-001": sub}
        )

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_subscription_skips_delivery(self) -> None:
        delivery = _make_delivery(payload={"event": "test"})
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks(
            [delivery],
            {},  # no subscription
        )

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_delivery_fires_task(self) -> None:
        payload = {"event": "assessment.completed", "data": {"id": "a1"}}
        delivery = _make_delivery(payload=payload, retry_count=2)
        sub = _make_subscription()
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks(
            [delivery], {"sub-001": sub}
        )

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("application.api_platform.webhook_service.attempt_delivery"),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            assert mock_create_task.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_deliveries_fires_one_task_each(self) -> None:
        payload = {"event": "test"}
        deliveries = [_make_delivery(delivery_id=f"del-00{i}", payload=payload) for i in range(3)]
        sub = _make_subscription()
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_mocks(
            deliveries, {"sub-001": sub}
        )

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch("asyncio.create_task") as mock_create_task,
        ):
            from application.api_platform import recovery_worker

            await recovery_worker._recover_pending()
            assert mock_create_task.call_count == 3


# ── Idempotency guard in attempt_delivery ─────────────────────────────────────


class TestAttemptDeliveryIdempotency:
    def _build_session_mock(self, delivery):
        mock_delivery_repo = MagicMock()
        mock_delivery_repo.get_by_id = AsyncMock(return_value=delivery)
        mock_delivery_repo.save = AsyncMock()

        mock_sub_repo = MagicMock()
        mock_sub_repo.get_by_id = AsyncMock(return_value=None)

        mock_factory = _make_session_ctx()

        return mock_factory, mock_delivery_repo, mock_sub_repo

    @pytest.mark.asyncio
    async def test_terminal_delivered_is_skipped(self) -> None:
        terminal = WebhookDelivery(
            id="del-t",
            subscription_id="sub-001",
            event_type="test",
            payload_hash="abc",
            delivery_status=WebhookDeliveryStatus.DELIVERED.value,
            status=EntityStatus.ACTIVE,
        )
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_session_mock(terminal)

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "application.api_platform.webhook_service.deliver_once",
                new=AsyncMock(return_value=(200, 50, None)),
            ),
        ):
            from application.api_platform.webhook_service import attempt_delivery

            await attempt_delivery(
                target_url="https://example.com/hook",
                secret="s3cr3t",
                payload={"event": "test"},
                event_type="test",
                delivery_id="del-t",
                attempt=0,
            )
            mock_delivery_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_terminal_dead_letter_is_skipped(self) -> None:
        terminal = WebhookDelivery(
            id="del-dl",
            subscription_id="sub-001",
            event_type="test",
            payload_hash="abc",
            delivery_status=WebhookDeliveryStatus.DEAD_LETTER.value,
            status=EntityStatus.ACTIVE,
        )
        mock_factory, mock_delivery_repo, mock_sub_repo = self._build_session_mock(terminal)

        with (
            patch("infrastructure.persistence.database.AsyncSessionFactory", mock_factory),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookDeliveryRepository",
                return_value=mock_delivery_repo,
            ),
            patch(
                "infrastructure.persistence.repositories.webhook.SQLWebhookSubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "application.api_platform.webhook_service.deliver_once",
                new=AsyncMock(return_value=(200, 50, None)),
            ),
        ):
            from application.api_platform.webhook_service import attempt_delivery

            await attempt_delivery(
                target_url="https://example.com/hook",
                secret="s3cr3t",
                payload={"event": "test"},
                event_type="test",
                delivery_id="del-dl",
                attempt=0,
            )
            mock_delivery_repo.save.assert_not_called()


# ── Retry schedule ─────────────────────────────────────────────────────────────


class TestRetrySchedule:
    def test_attempt_5_and_beyond_returns_none(self) -> None:
        from application.api_platform.webhook_service import next_retry_at

        assert next_retry_at(5) is None
        assert next_retry_at(6) is None

    def test_attempts_below_5_return_datetime(self) -> None:
        from application.api_platform.webhook_service import next_retry_at

        for attempt in range(5):
            assert next_retry_at(attempt) is not None

    def test_retry_delays_are_non_decreasing(self) -> None:
        from application.api_platform.webhook_service import _RETRY_DELAYS_SECONDS

        for i in range(len(_RETRY_DELAYS_SECONDS) - 1):
            assert _RETRY_DELAYS_SECONDS[i] <= _RETRY_DELAYS_SECONDS[i + 1]
