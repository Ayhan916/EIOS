"""Thin audit helper for AI Governance services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from infrastructure.persistence.models.audit_event import AuditEventModel


def emit_audit_event(
    *,
    session: Session,
    event_type: str,
    actor_id: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(
        AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=event_type,
            actor_id=actor_id,
            entity_type=resource_type,
            entity_id=resource_id,
            outcome="success",
            detail=None,
            event_metadata=details or {},
        )
    )
