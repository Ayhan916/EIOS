"""
Webhook Recovery Worker

Scans the webhook_deliveries table every 60 seconds for deliveries that are:
  - status = "failed"
  - retry_at <= now()
  - retry_count < MAX_ATTEMPTS

and re-queues them via asyncio tasks.

Restart-safe: retry_at timestamps are persisted in DB; worker picks up
where it left off after restart.

Idempotent: attempt_delivery() guards against re-delivering terminal records.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

log = structlog.get_logger("webhook_recovery")

_POLL_INTERVAL_SECONDS = 60
_BATCH_SIZE = 100


async def run_webhook_recovery_loop() -> None:
    """Long-running recovery loop. Run as asyncio.create_task() at startup."""
    log.info("webhook_recovery_started", poll_interval=_POLL_INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        try:
            await _recover_pending()
        except Exception as exc:  # noqa: BLE001
            log.error("webhook_recovery_error", error=str(exc))


async def _recover_pending() -> None:
    from application.api_platform.webhook_service import attempt_delivery  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.webhook import (  # noqa: PLC0415
        SQLWebhookDeliveryRepository,
        SQLWebhookSubscriptionRepository,
    )

    now = datetime.now(UTC)
    async with AsyncSessionFactory() as session, session.begin():
        delivery_repo = SQLWebhookDeliveryRepository(session)
        due = await delivery_repo.list_pending_retries(now)

    if not due:
        return

    log.info("webhook_recovery_tick", due_count=len(due))

    # Load subscription secrets outside the session (session already closed above)
    # We need a fresh session for each sub lookup, or load them all at once.
    # Batch-load unique subscription IDs to avoid N queries.
    sub_ids = list({d.subscription_id for d in due})
    sub_map: dict[str, tuple[str, str]] = {}  # sub_id → (target_url, secret)

    async with AsyncSessionFactory() as session, session.begin():
        sub_repo = SQLWebhookSubscriptionRepository(session)
        for sid in sub_ids:
            sub = await sub_repo.get_by_id(sid)
            if sub and sub.is_active:
                sub_map[sid] = (sub.target_url, sub.secret)

    fired = 0
    for delivery in due[:_BATCH_SIZE]:
        target = sub_map.get(delivery.subscription_id)
        if not target:
            continue  # subscription deleted or disabled — skip
        if not delivery.payload:
            log.warning("webhook_recovery_no_payload", delivery_id=delivery.id)
            continue  # legacy delivery without stored payload — cannot retry
        target_url, secret = target
        asyncio.create_task(
            attempt_delivery(
                target_url=target_url,
                secret=secret,
                payload=delivery.payload,
                event_type=delivery.event_type,
                delivery_id=delivery.id,
                attempt=delivery.retry_count,
            )
        )
        fired += 1

    if fired:
        log.info("webhook_recovery_dispatched", count=fired)
