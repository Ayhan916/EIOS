"""Evaluation Engine API — GAP-02 / FR-014.

Endpoints:
  POST /evaluation/run            Trigger a manual evaluation run
  GET  /evaluation/latest         Latest evaluation snapshot
  GET  /evaluation/trends         Time series (last N runs)
  GET  /evaluation/benchmarks     Benchmark results for a run
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from application.evaluation.evaluation_service import run_evaluation
from domain.evaluation import BenchmarkResult, EvaluationRun
from infrastructure.persistence.repositories.evaluation import (
    SQLBenchmarkResultRepository,
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
