from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkflowJobResponse(BaseModel):
    id: str
    workflow_type: str
    query: str
    job_status: str
    workflow_run_id: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WorkflowJobListResponse(BaseModel):
    jobs: list[WorkflowJobResponse]
    total: int
