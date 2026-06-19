"""M34.1/M34.2 External Intelligence Operations Router.

Admin-only endpoints for managing live intelligence connectors and
monitoring data freshness. All endpoints require require_admin (B2).

Endpoints:
  GET  /external-intelligence/operations/dashboard
  GET  /external-intelligence/operations/health
  GET  /external-intelligence/operations/health/{connector_name}
  GET  /external-intelligence/operations/freshness
  POST /external-intelligence/operations/trigger
  GET  /external-intelligence/operations/scheduler-health
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.external_intelligence.health_service import (
    classify_overall_health,
    get_all_connector_health,
    get_connector_health,
)
from application.external_intelligence.freshness_service import get_freshness_dashboard
from application.external_intelligence.metrics import ext_counters
from application.external_intelligence.scheduler import trigger_connector_refresh
from application.external_intelligence.scheduler_health import get_scheduler_health_report
from interfaces.api.deps import get_db, require_admin
from interfaces.api.schemas.operations import (
    ConnectorHealthListResponse,
    ConnectorHealthResponse,
    ConnectorTriggerRequest,
    ConnectorTriggerResponse,
    DatasetFreshnessListResponse,
    DatasetFreshnessResponse,
    OperationsDashboardResponse,
    SchedulerHealthResponse,
)

router = APIRouter(prefix="/external-intelligence/operations", tags=["Operations"])

# B2: all operations endpoints require admin role
_ADMIN = Depends(require_admin)


# ── Dashboard ──────────────────────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=OperationsDashboardResponse,
    dependencies=[_ADMIN],
    summary="Operations dashboard summary (admin only)",
)
async def get_operations_dashboard(
    db: AsyncSession = Depends(get_db),
) -> OperationsDashboardResponse:
    """Platform-level connector health and data freshness summary."""
    healths = await get_all_connector_health(db)
    freshness_list = await get_freshness_dashboard(db)

    from domain.enums import ConnectorStatus, FreshnessStatus

    fresh = sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.FRESH.value)
    stale = sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.STALE.value)
    expired = sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.EXPIRED.value)

    healthy_c = sum(1 for h in healths if h.status == ConnectorStatus.HEALTHY.value)
    degraded_c = sum(1 for h in healths if h.status == ConnectorStatus.DEGRADED.value)
    failed_c = sum(1 for h in healths if h.status == ConnectorStatus.FAILED.value)

    return OperationsDashboardResponse(
        overall_health=classify_overall_health(healths),
        fresh_datasets=fresh,
        stale_datasets=stale,
        expired_datasets=expired,
        total_connectors=len(healths),
        healthy_connectors=healthy_c,
        degraded_connectors=degraded_c,
        failed_connectors=failed_c,
        dataset_refresh_total=ext_counters.dataset_refresh_total,
        dataset_refresh_failed_total=ext_counters.dataset_refresh_failed_total,
        sanctions_updates_total=ext_counters.sanctions_updates_total,
        benchmark_refresh_total=ext_counters.benchmark_refresh_total,
    )


# ── Connector Health ───────────────────────────────────────────────────────────


@router.get(
    "/health",
    response_model=ConnectorHealthListResponse,
    dependencies=[_ADMIN],
    summary="All connector health statuses (admin only)",
)
async def list_connector_health(
    db: AsyncSession = Depends(get_db),
) -> ConnectorHealthListResponse:
    healths = await get_all_connector_health(db)
    overall = classify_overall_health(healths)
    items = [
        ConnectorHealthResponse(
            connector_name=h.connector_name,
            status=h.status,
            last_success=h.last_success,
            last_failure=h.last_failure,
            total_runs=h.total_runs,
            successful_runs=h.successful_runs,
            failed_runs=h.failed_runs,
            avg_runtime_seconds=h.avg_runtime_seconds,
            consecutive_failures=h.consecutive_failures,
        )
        for h in healths
    ]
    return ConnectorHealthListResponse(items=items, overall_status=overall, total=len(items))


@router.get(
    "/health/{connector_name}",
    response_model=ConnectorHealthResponse,
    dependencies=[_ADMIN],
    summary="Single connector health (admin only)",
)
async def get_single_connector_health(
    connector_name: str,
    db: AsyncSession = Depends(get_db),
) -> ConnectorHealthResponse:
    h = await get_connector_health(connector_name, db)
    return ConnectorHealthResponse(
        connector_name=h.connector_name,
        status=h.status,
        last_success=h.last_success,
        last_failure=h.last_failure,
        total_runs=h.total_runs,
        successful_runs=h.successful_runs,
        failed_runs=h.failed_runs,
        avg_runtime_seconds=h.avg_runtime_seconds,
        consecutive_failures=h.consecutive_failures,
    )


# ── Dataset Freshness ──────────────────────────────────────────────────────────


@router.get(
    "/freshness",
    response_model=DatasetFreshnessListResponse,
    dependencies=[_ADMIN],
    summary="Dataset freshness for all sources (admin only)",
)
async def list_dataset_freshness(
    db: AsyncSession = Depends(get_db),
) -> DatasetFreshnessListResponse:
    from domain.enums import FreshnessStatus

    freshness_list = await get_freshness_dashboard(db)
    items = [
        DatasetFreshnessResponse(
            source_name=f.source_name,
            freshness_status=f.freshness_status,
            last_refresh=f.last_refresh,
            expected_cadence_hours=f.expected_cadence_hours,
            hours_since_refresh=f.hours_since_refresh,
            hours_overdue=f.hours_overdue,
            next_expected_refresh=f.next_expected_refresh,
        )
        for f in freshness_list
    ]
    return DatasetFreshnessListResponse(
        items=items,
        stale_count=sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.STALE.value),
        expired_count=sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.EXPIRED.value),
        fresh_count=sum(1 for f in freshness_list if f.freshness_status == FreshnessStatus.FRESH.value),
    )


# ── Manual Trigger (H5: full pipeline) ────────────────────────────────────────


@router.post(
    "/trigger",
    response_model=ConnectorTriggerResponse,
    dependencies=[_ADMIN],
    summary="Manually trigger a connector refresh + benchmark refresh (admin only)",
    status_code=status.HTTP_200_OK,
)
async def trigger_refresh(
    body: ConnectorTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> ConnectorTriggerResponse:
    """Run a connector refresh and, on success, trigger benchmark refresh.

    H5: Identical pipeline to the scheduler — validation → dataset activation
    → benchmark refresh → enrichment refresh.
    """
    try:
        result = await trigger_connector_refresh(
            body.connector_name,
            db,
            trigger_source="manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connector run failed: {exc}",
        ) from exc

    # H5: trigger benchmark refresh for manual runs too
    if result.success and result.dataset_id:
        try:
            from application.external_intelligence.benchmark_refresh_service import (
                refresh_for_dataset,
            )
            await refresh_for_dataset(result.dataset_id, body.connector_name, db)
        except Exception:
            pass  # benchmark refresh failure does not fail the trigger response

    return ConnectorTriggerResponse(
        connector_name=result.connector_name,
        success=result.success,
        row_count=result.row_count,
        runtime_seconds=result.runtime_seconds,
        dataset_id=result.dataset_id,
        error_message=result.error_message,
    )


# ── Scheduler Health (M6) ──────────────────────────────────────────────────────


@router.get(
    "/scheduler-health",
    response_model=SchedulerHealthResponse,
    dependencies=[_ADMIN],
    summary="Scheduler liveness and last cycle timestamps (admin only)",
)
async def get_scheduler_health() -> SchedulerHealthResponse:
    """Return scheduler liveness state from the in-process heartbeat."""
    report = get_scheduler_health_report()
    return SchedulerHealthResponse(
        scheduler_alive=report.scheduler_alive,
        last_cycle_started=report.last_cycle_started,
        last_cycle_completed=report.last_cycle_completed,
        seconds_since_last_cycle=report.seconds_since_last_cycle,
        cycles_completed=report.cycles_completed,
    )
