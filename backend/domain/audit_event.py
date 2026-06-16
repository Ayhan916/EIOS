from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class AuditEvent(BaseEntity):
    """Immutable record of a significant system action.

    Written once; never updated. Status field (from BaseEntity) is always
    ACTIVE for audit events — the status lifecycle does not apply here.
    The entity_type + entity_id pair identifies the object acted upon.
    """

    action: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    outcome: str = "success"
    detail: Optional[str] = None
    event_metadata: dict = field(default_factory=dict)
