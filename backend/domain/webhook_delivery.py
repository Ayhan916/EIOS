from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class WebhookDelivery(BaseEntity):
    """A single delivery attempt for a webhook event."""

    subscription_id: str = ""
    event_type: str = ""
    payload_hash: str = ""
    payload: dict[str, Any] | None = None
    delivery_status: str = "pending"
    response_code: int | None = None
    duration_ms: int | None = None
    retry_count: int = 0
    retry_at: datetime | None = None
    error_message: str | None = None
    delivered_at: datetime | None = None
