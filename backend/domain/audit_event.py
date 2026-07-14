from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class AuditEvent(BaseEntity):
    """Immutable record of a significant system action.

    Written once; never updated. Status field (from BaseEntity) is always
    ACTIVE for audit events — the status lifecycle does not apply here.
    The entity_type + entity_id pair identifies the object acted upon.

    ADR-006: entry_hash is the SHA-256 of this entry chained to the previous
    entry's hash. Set by the repository on save — callers leave it as None.
    """

    action: str
    actor_id: str | None = None
    actor_email: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    outcome: str = "success"
    detail: str | None = None
    event_metadata: dict[str, Any] = field(default_factory=dict)
    previous_hash: str | None = None
    entry_hash: str | None = None
