from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True, kw_only=True)
class WorkflowJob:
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_type: str
    query: str
    created_by: str | None = None
    organization_id: str | None = None
    job_status: str = "pending"  # pending | running | completed | failed
    workflow_run_id: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    job_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
