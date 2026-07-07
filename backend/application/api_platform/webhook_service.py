"""
Webhook dispatch, signing, and retry logic.

Signing: HMAC-SHA256 over the canonical JSON body.
Retry schedule:
  attempt 0 → immediate
  attempt 1 → +1 min
  attempt 2 → +5 min
  attempt 3 → +15 min
  attempt 4 → +60 min
  attempt 5 → dead_letter
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

_RETRY_DELAYS_SECONDS = [0, 60, 300, 900, 3600]
_MAX_ATTEMPTS = 5
_DELIVERY_TIMEOUT = 10.0  # seconds


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    """Return HMAC-SHA256 signature for X-EIOS-Signature header."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def canonical_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_body(payload)).hexdigest()


async def deliver_once(
    target_url: str,
    payload: dict[str, Any],
    secret: str,
    event_type: str,
    delivery_id: str,
) -> tuple[int | None, int, str | None]:
    """Attempt a single HTTP POST delivery.

    Returns (response_code, duration_ms, error_message).
    """
    body = canonical_body(payload)
    signature = f"sha256={hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}"
    headers = {
        "Content-Type": "application/json",
        "X-EIOS-Event": event_type,
        "X-EIOS-Delivery": delivery_id,
        "X-EIOS-Signature": signature,
    }
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_DELIVERY_TIMEOUT) as client:
            resp = await client.post(target_url, content=body, headers=headers)
        duration_ms = int((time.monotonic() - t0) * 1000)
        if resp.is_success:
            return resp.status_code, duration_ms, None
        return resp.status_code, duration_ms, f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - t0) * 1000)
        return None, duration_ms, str(exc)[:500]


def next_retry_at(attempt: int) -> datetime | None:
    """Return the datetime of the next retry, or None if max attempts reached."""
    if attempt >= _MAX_ATTEMPTS:
        return None
    delay = (
        _RETRY_DELAYS_SECONDS[attempt]
        if attempt < len(_RETRY_DELAYS_SECONDS)
        else _RETRY_DELAYS_SECONDS[-1]
    )
    return datetime.now(UTC) + timedelta(seconds=delay)


async def attempt_delivery(
    target_url: str,
    secret: str,
    payload: dict,
    event_type: str,
    delivery_id: str,
    attempt: int = 0,
) -> None:
    """Execute one delivery attempt and persist the result.

    Self-contained: creates its own DB session.  Safe to call from background
    tasks, the recovery worker, and asyncio.create_task().

    Idempotency guard: if the delivery is already in a terminal state
    (delivered, dead_letter) this function returns immediately without
    re-delivering — prevents duplicate deliveries after a restart.
    """
    from domain.enums import WebhookDeliveryStatus  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.repositories.webhook import (  # noqa: PLC0415
        SQLWebhookDeliveryRepository,
        SQLWebhookSubscriptionRepository,
    )

    _TERMINAL = {WebhookDeliveryStatus.DELIVERED.value, WebhookDeliveryStatus.DEAD_LETTER.value}

    response_code, duration_ms, error = await deliver_once(
        target_url, payload, secret, event_type, delivery_id
    )
    now = datetime.now(UTC)
    success = response_code is not None and 200 <= response_code < 300

    async with AsyncSessionFactory() as session, session.begin():
        delivery_repo = SQLWebhookDeliveryRepository(session)
        delivery = await delivery_repo.get_by_id(delivery_id)
        if delivery is None:
            return
        # Idempotency: never re-process a terminal delivery
        if delivery.delivery_status in _TERMINAL:
            return
        delivery.response_code = response_code
        delivery.duration_ms = duration_ms
        delivery.retry_count = attempt
        is_dead_letter = False
        if success:
            delivery.delivery_status = WebhookDeliveryStatus.DELIVERED.value
            delivery.delivered_at = now
        else:
            next_attempt = attempt + 1
            ra = next_retry_at(next_attempt)
            if ra is None:
                delivery.delivery_status = WebhookDeliveryStatus.DEAD_LETTER.value
                delivery.error_message = error or "Max retries exceeded"
                is_dead_letter = True
                log.warning(
                    "webhook.dead_letter", delivery_id=delivery_id, url=target_url, error=error
                )
            else:
                delivery.delivery_status = WebhookDeliveryStatus.FAILED.value
                delivery.retry_at = ra
                delivery.error_message = error
        await delivery_repo.save(delivery)

        # Update in-process metrics counter
        try:
            from interfaces.api.routers.metrics import counters  # noqa: PLC0415

            counters.record_webhook_delivery(succeeded=success, dead_letter=is_dead_letter)
        except Exception:  # noqa: BLE001
            pass

        if not success:
            sub_repo = SQLWebhookSubscriptionRepository(session)
            sub = await sub_repo.get_by_id(delivery.subscription_id)
            if sub:
                sub.failure_count = (sub.failure_count or 0) + 1
                await sub_repo.save(sub)

    if not success and attempt + 1 < _MAX_ATTEMPTS:
        ra = next_retry_at(attempt + 1)
        if ra:
            delay = (ra - datetime.now(UTC)).total_seconds()
            await asyncio.sleep(max(0.0, delay))
            await attempt_delivery(
                target_url, secret, payload, event_type, delivery_id, attempt + 1
            )
