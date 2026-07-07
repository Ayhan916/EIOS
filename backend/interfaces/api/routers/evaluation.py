"""Evaluation Engine API — GAP-02 / FR-014 + GAP-03 Mission Control.

Endpoints:
  POST /evaluation/run              Trigger a manual evaluation run
  GET  /evaluation/latest           Latest evaluation snapshot
  GET  /evaluation/trends           Time series (last N runs)
  GET  /evaluation/benchmarks/{id}  Benchmark results for a run
  GET  /evaluation/system-status    Mission Control summary (health + agent counts)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from application.evaluation.evaluation_service import run_evaluation
from domain.evaluation import BenchmarkResult, CalibrationEvent, EvaluationRun
from infrastructure.persistence.repositories.evaluation import (
    SQLBenchmarkResultRepository,
    SQLCalibrationEventRepository,
    SQLEvaluationRunRepository,
)
from interfaces.api.deps import get_current_user, get_db, require_analyst

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# ── Schemas ────────────────────────────────────────────────────────────────────


class EvaluationRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    run_type: str
    window_days: int
    agent_run_count: int
    accuracy_score: float
    precision_score: float
    recall_score: float
    confidence_score: float
    hallucination_rate: float
    error_rate: float
    cost_usd_total: float
    cost_usd_last_7d: float
    cost_usd_last_30d: float
    benchmark_status: str
    benchmark_passed: int
    benchmark_total: int
    platform_health_score: float
    raw_metrics: dict
    computed_at: datetime | None
    created_at: datetime


class BenchmarkResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    evaluation_run_id: str
    benchmark_name: str
    module: str
    dimension: str
    passed: bool
    score: float
    expected_output: str
    actual_output: str
    failure_reason: str
    duration_ms: float
    created_at: datetime


class TriggerResponse(BaseModel):
    evaluation_run: EvaluationRunResponse
    benchmark_results: list[BenchmarkResultResponse]


class TrendsResponse(BaseModel):
    runs: list[EvaluationRunResponse]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _run_to_response(r: EvaluationRun) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=r.id,
        run_type=r.run_type,
        window_days=r.window_days,
        agent_run_count=r.agent_run_count,
        accuracy_score=r.accuracy_score,
        precision_score=r.precision_score,
        recall_score=r.recall_score,
        confidence_score=r.confidence_score,
        hallucination_rate=r.hallucination_rate,
        error_rate=r.error_rate,
        cost_usd_total=r.cost_usd_total,
        cost_usd_last_7d=r.cost_usd_last_7d,
        cost_usd_last_30d=r.cost_usd_last_30d,
        benchmark_status=r.benchmark_status,
        benchmark_passed=r.benchmark_passed,
        benchmark_total=r.benchmark_total,
        platform_health_score=r.platform_health_score,
        raw_metrics=r.raw_metrics,
        computed_at=r.computed_at,
        created_at=r.created_at,
    )


def _bm_to_response(b: BenchmarkResult) -> BenchmarkResultResponse:
    return BenchmarkResultResponse(
        id=b.id,
        evaluation_run_id=b.evaluation_run_id,
        benchmark_name=b.benchmark_name,
        module=b.module,
        dimension=b.dimension,
        passed=b.passed,
        score=b.score,
        expected_output=b.expected_output,
        actual_output=b.actual_output,
        failure_reason=b.failure_reason,
        duration_ms=b.duration_ms,
        created_at=b.created_at,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/run",
    response_model=TriggerResponse,
    dependencies=[Depends(require_analyst)],
    summary="Trigger a manual evaluation run",
)
async def trigger_evaluation(
    window_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> TriggerResponse:
    """Runs the benchmark suite and computes live metrics from agent_runs.

    Results are deterministic for the benchmark portion; live metrics
    reflect the actual agent run history in the evaluation window.
    """
    evaluation_run, bm_results = await run_evaluation(
        db,
        run_type="manual",
        window_days=window_days,
        triggered_by=str(current_user.id),
    )

    run_repo = SQLEvaluationRunRepository(db)
    bm_repo = SQLBenchmarkResultRepository(db)

    await run_repo.create(evaluation_run)
    for bm in bm_results:
        await bm_repo.create(bm)
    await db.commit()

    return TriggerResponse(
        evaluation_run=_run_to_response(evaluation_run),
        benchmark_results=[_bm_to_response(b) for b in bm_results],
    )


@router.get(
    "/latest",
    response_model=EvaluationRunResponse | None,
    dependencies=[Depends(require_analyst)],
    summary="Latest evaluation snapshot",
)
async def get_latest(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> EvaluationRunResponse | None:
    repo = SQLEvaluationRunRepository(db)
    run = await repo.get_latest()
    return _run_to_response(run) if run else None


@router.get(
    "/trends",
    response_model=TrendsResponse,
    dependencies=[Depends(require_analyst)],
    summary="Time series of recent evaluation runs",
)
async def get_trends(
    limit: int = Query(default=12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> TrendsResponse:
    repo = SQLEvaluationRunRepository(db)
    runs = await repo.list_recent(limit=limit)
    return TrendsResponse(runs=[_run_to_response(r) for r in runs])


@router.get(
    "/benchmarks/{run_id}",
    response_model=list[BenchmarkResultResponse],
    dependencies=[Depends(require_analyst)],
    summary="Benchmark results for a specific evaluation run",
)
async def get_benchmarks(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> list[BenchmarkResultResponse]:
    repo = SQLBenchmarkResultRepository(db)
    results = await repo.list_by_run(run_id)
    return [_bm_to_response(b) for b in results]


# ── Mission Control system-status ──────────────────────────────────────────────


# ── Benchmark Comparison (GAP-21) ─────────────────────────────────────────────


class BenchmarkTrendPoint(BaseModel):
    run_id: str
    computed_at: str | None
    pass_rate: float
    passed: int
    total: int


class ModuleComparisonEntry(BaseModel):
    module: str
    current_pass_rate: float
    prev_pass_rate: float | None
    delta: float | None
    status: str  # "green" | "yellow" | "red" | "unknown"
    baseline: float  # target pass rate (1.0 for deterministic benchmarks)
    total_cases: int
    passed_cases: int
    trend: list[BenchmarkTrendPoint]
    failing_cases: list[str]


class BenchmarkComparisonResponse(BaseModel):
    modules: list[ModuleComparisonEntry]
    run_count: int
    latest_run_id: str | None
    latest_computed_at: str | None


def _bm_status(pass_rate: float) -> str:
    if pass_rate >= 0.90:
        return "green"
    elif pass_rate >= 0.70:
        return "yellow"
    else:
        return "red"


@router.get(
    "/benchmarks/comparison",
    response_model=BenchmarkComparisonResponse,
    dependencies=[Depends(require_analyst)],
    summary="Contextual benchmark comparison across modules and runs (GAP-21)",
)
async def get_benchmark_comparison(
    limit_runs: int = Query(default=5, ge=2, le=20),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> BenchmarkComparisonResponse:
    """Deterministic module ranking with delta-to-previous and sparkline trend.

    Returns all modules sorted by current_pass_rate ascending (worst first),
    so the most critical modules appear at the top.
    """
    run_repo = SQLEvaluationRunRepository(db)
    bm_repo = SQLBenchmarkResultRepository(db)

    recent_runs = await run_repo.list_recent(limit=limit_runs)
    if not recent_runs:
        return BenchmarkComparisonResponse(
            modules=[], run_count=0, latest_run_id=None, latest_computed_at=None
        )

    # chronological order (oldest first) for trend sparklines
    runs_chron = list(reversed(recent_runs))
    run_ids = [r.id for r in runs_chron]
    run_map = {r.id: r for r in runs_chron}

    all_bm = await bm_repo.list_by_run_ids(run_ids)

    # Group: module → run_id → list[BenchmarkResult]
    from collections import defaultdict

    by_module_run: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for bm in all_bm:
        by_module_run[bm.module][bm.evaluation_run_id].append(bm)

    latest_run = recent_runs[0]  # most recent
    prev_run = recent_runs[1] if len(recent_runs) > 1 else None

    entries: list[ModuleComparisonEntry] = []

    for module, run_bm_map in by_module_run.items():
        # Build trend (chronological)
        trend: list[BenchmarkTrendPoint] = []
        for rid in run_ids:
            bms = run_bm_map.get(rid, [])
            if not bms:
                continue
            passed = sum(1 for b in bms if b.passed)
            total = len(bms)
            run_obj = run_map[rid]
            trend.append(
                BenchmarkTrendPoint(
                    run_id=rid,
                    computed_at=run_obj.computed_at.isoformat() if run_obj.computed_at else None,
                    pass_rate=round(passed / total, 4) if total else 0.0,
                    passed=passed,
                    total=total,
                )
            )

        # Current pass rate (from latest run)
        latest_bms = run_bm_map.get(latest_run.id, [])
        if not latest_bms:
            continue
        cur_passed = sum(1 for b in latest_bms if b.passed)
        cur_total = len(latest_bms)
        current_pass_rate = round(cur_passed / cur_total, 4) if cur_total else 0.0

        # Previous pass rate
        prev_pass_rate: float | None = None
        delta: float | None = None
        if prev_run:
            prev_bms = run_bm_map.get(prev_run.id, [])
            if prev_bms:
                pp = sum(1 for b in prev_bms if b.passed)
                pt = len(prev_bms)
                prev_pass_rate = round(pp / pt, 4) if pt else 0.0
                delta = round(current_pass_rate - prev_pass_rate, 4)

        failing_cases = [b.benchmark_name for b in latest_bms if not b.passed]

        entries.append(
            ModuleComparisonEntry(
                module=module,
                current_pass_rate=current_pass_rate,
                prev_pass_rate=prev_pass_rate,
                delta=delta,
                status=_bm_status(current_pass_rate),
                baseline=1.0,
                total_cases=cur_total,
                passed_cases=cur_passed,
                trend=trend,
                failing_cases=failing_cases,
            )
        )

    # Sort: worst first (ascending pass_rate)
    entries.sort(key=lambda e: e.current_pass_rate)

    return BenchmarkComparisonResponse(
        modules=entries,
        run_count=len(recent_runs),
        latest_run_id=latest_run.id,
        latest_computed_at=latest_run.computed_at.isoformat() if latest_run.computed_at else None,
    )


class AgentStatusSummary(BaseModel):
    active: int
    idle: int
    error: int
    disabled: int
    total: int


class SystemStatusResponse(BaseModel):
    platform_health_score: float
    benchmark_status: str
    benchmark_passed: int
    benchmark_total: int
    accuracy_score: float
    confidence_score: float
    hallucination_rate: float
    error_rate: float
    cost_usd_last_7d: float
    cost_usd_last_30d: float
    agent_run_count: int
    latest_run_id: str | None
    computed_at: str | None
    agents: AgentStatusSummary


@router.get(
    "/system-status",
    response_model=SystemStatusResponse,
    dependencies=[Depends(require_analyst)],
    summary="Mission Control — platform health + agent summary in one call",
)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> SystemStatusResponse:
    """Single-call endpoint for the Mission Control Dashboard header."""
    from sqlalchemy import func as sqlfunc
    from sqlalchemy import select as sqselect

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    run_repo = SQLEvaluationRunRepository(db)
    latest = await run_repo.get_latest()

    # Agent status counts
    stmt = sqselect(MonitoringAgentModel.status, sqlfunc.count().label("n")).group_by(
        MonitoringAgentModel.status
    )
    result = await db.execute(stmt)
    counts: dict[str, int] = {row.status: row.n for row in result.all()}

    agents = AgentStatusSummary(
        active=counts.get("ACTIVE", 0),
        idle=counts.get("IDLE", 0),
        error=counts.get("ERROR", 0),
        disabled=counts.get("DISABLED", 0),
        total=sum(counts.values()),
    )

    if latest is None:
        return SystemStatusResponse(
            platform_health_score=0.0,
            benchmark_status="unknown",
            benchmark_passed=0,
            benchmark_total=0,
            accuracy_score=0.0,
            confidence_score=0.0,
            hallucination_rate=0.0,
            error_rate=0.0,
            cost_usd_last_7d=0.0,
            cost_usd_last_30d=0.0,
            agent_run_count=0,
            latest_run_id=None,
            computed_at=None,
            agents=agents,
        )

    return SystemStatusResponse(
        platform_health_score=latest.platform_health_score,
        benchmark_status=latest.benchmark_status,
        benchmark_passed=latest.benchmark_passed,
        benchmark_total=latest.benchmark_total,
        accuracy_score=latest.accuracy_score,
        confidence_score=latest.confidence_score,
        hallucination_rate=latest.hallucination_rate,
        error_rate=latest.error_rate,
        cost_usd_last_7d=latest.cost_usd_last_7d,
        cost_usd_last_30d=latest.cost_usd_last_30d,
        agent_run_count=latest.agent_run_count,
        latest_run_id=latest.id,
        computed_at=latest.computed_at.isoformat() if latest.computed_at else None,
        agents=agents,
    )


# ── Confidence Calibration (GAP-27) ───────────────────────────────────────────

_VALID_CONFIDENCE = {"high", "medium", "low"}
_VALID_OUTCOME = {"confirmed", "refuted", "unknown"}
_VALID_ENTITY_TYPE = {"finding", "risk", "recommendation"}


class RecordCalibrationRequest(BaseModel):
    entity_type: str  # "finding" | "risk" | "recommendation"
    entity_id: str
    predicted_confidence: str  # "high" | "medium" | "low"
    actual_outcome: str  # "confirmed" | "refuted" | "unknown"


class CalibrationEventResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    predicted_confidence: str
    actual_outcome: str
    recorded_by: str | None
    recorded_at: datetime | None
    created_at: datetime


class CalibrationPoint(BaseModel):
    confidence_level: str  # "high" | "medium" | "low"
    total: int
    confirmed: int
    refuted: int
    unknown: int
    accuracy: float | None  # confirmed / (confirmed + refuted), None if no decisive events


class CalibrationCurveResponse(BaseModel):
    points: list[CalibrationPoint]
    total_events: int


@router.post(
    "/calibration/events",
    response_model=CalibrationEventResponse,
    dependencies=[Depends(require_analyst)],
    summary="Record a calibration event (analyst records actual outcome) — GAP-27",
)
async def record_calibration_event(
    body: RecordCalibrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> CalibrationEventResponse:
    """Analyst records whether a confidence prediction was accurate.

    This endpoint is for human analysts only — AI agents must not call it.
    """
    import uuid

    if body.entity_type not in _VALID_ENTITY_TYPE:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422, detail=f"entity_type must be one of {_VALID_ENTITY_TYPE}"
        )
    if body.predicted_confidence not in _VALID_CONFIDENCE:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422, detail=f"predicted_confidence must be one of {_VALID_CONFIDENCE}"
        )
    if body.actual_outcome not in _VALID_OUTCOME:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422, detail=f"actual_outcome must be one of {_VALID_OUTCOME}"
        )

    now = datetime.now(__import__("datetime").timezone.utc)
    event = CalibrationEvent(
        id=str(uuid.uuid4()),
        organization_id=str(current_user.organization_id),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        predicted_confidence=body.predicted_confidence,
        actual_outcome=body.actual_outcome,
        recorded_by=str(current_user.id),
        recorded_at=now,
        created_by=str(current_user.id),
        created_at=now,
        updated_at=now,
    )

    repo = SQLCalibrationEventRepository(db)
    saved = await repo.save(event)
    await db.commit()

    return CalibrationEventResponse(
        id=saved.id,
        entity_type=saved.entity_type,
        entity_id=saved.entity_id,
        predicted_confidence=saved.predicted_confidence,
        actual_outcome=saved.actual_outcome,
        recorded_by=saved.recorded_by,
        recorded_at=saved.recorded_at,
        created_at=saved.created_at,
    )


@router.get(
    "/calibration/curve",
    response_model=CalibrationCurveResponse,
    dependencies=[Depends(require_analyst)],
    summary="Confidence calibration curve — per-level accuracy stats — GAP-27",
)
async def get_calibration_curve(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> CalibrationCurveResponse:
    """Returns calibration accuracy grouped by predicted confidence level.

    Accuracy = confirmed / (confirmed + refuted) per confidence band.
    Deterministic computation — no LLM involved.
    """
    repo = SQLCalibrationEventRepository(db)
    rows = await repo.compute_curve(str(current_user.organization_id))

    points = [CalibrationPoint(**row) for row in rows]
    total_events = sum(p.total for p in points)

    return CalibrationCurveResponse(points=points, total_events=total_events)
