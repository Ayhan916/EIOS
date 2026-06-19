from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class WebhookSubscription(BaseEntity):
    """Outbound webhook subscription for a tenant."""

    organization_id: str
    name: str = ""
    target_url: str = ""
    secret: str = ""
    events: list[str] = field(default_factory=list)
    is_active: bool = True
    failure_count: int = 0
    last_triggered_at: datetime | None = None
