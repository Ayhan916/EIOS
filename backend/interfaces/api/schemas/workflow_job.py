from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkflowJobResponse(BaseModel):
    id: str
    workflow_type: str
    query: str
    job_status: str
    workflow_run_id: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowJobListResponse(BaseModel):
    jobs: list[WorkflowJobResponse]
    total: int
