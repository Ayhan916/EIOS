"""M34.1 Operations API Schemas.

Pydantic models for the /external-intelligence/operations admin endpoints:
  - connector health
  - dataset freshness
  - manual trigger
  - validation results
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConnectorHealthResponse(BaseModel):
    connector_name: str
    status: str
    last_success: datetime | None
    last_failure: datetime | None
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_runtime_seconds: float
    consecutive_failures: int


class ConnectorHealthListResponse(BaseModel):
    items: list[ConnectorHealthResponse]
    overall_status: str
    total: int


class DatasetFreshnessResponse(BaseModel):
    source_name: str
    freshness_status: str
    last_refresh: datetime | None
    expected_cadence_hours: int
    hours_since_refresh: float | None
    hours_overdue: float
    next_expected_refresh: datetime | None


class DatasetFreshnessListResponse(BaseModel):
    items: list[DatasetFreshnessResponse]
    stale_count: int
    expired_count: int
    fresh_count: int


class ConnectorTriggerRequest(BaseModel):
    connector_name: str


class ConnectorTriggerResponse(BaseModel):
    connector_name: str
    success: bool
    row_count: int
    runtime_seconds: float
    dataset_id: str | None
    error_message: str | None


class ValidationResultResponse(BaseModel):
    dataset_id: str
    source_name: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    row_count: int
    duplicate_count: int
    validated_at: datetime


class SchedulerHealthResponse(BaseModel):
    scheduler_alive: bool
    last_cycle_started: datetime | None
    last_cycle_completed: datetime | None
    seconds_since_last_cycle: float | None
    cycles_completed: int


class OperationsDashboardResponse(BaseModel):
    overall_health: str
    fresh_datasets: int
    stale_datasets: int
    expired_datasets: int
    total_connectors: int
    healthy_connectors: int
    degraded_connectors: int
    failed_connectors: int
    dataset_refresh_total: int
    dataset_refresh_failed_total: int
    sanctions_updates_total: int
    benchmark_refresh_total: int
