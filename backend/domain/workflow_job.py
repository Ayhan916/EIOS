from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, kw_only=True)
class WorkflowJob:
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_type: str
    query: str
    created_by: Optional[str] = None
    organization_id: Optional[str] = None
    job_status: str = "pending"  # pending | running | completed | failed
    workflow_run_id: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    job_metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
