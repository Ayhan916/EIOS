"""Repositories for EvaluationRun and BenchmarkResult (GAP-02)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.evaluation import BenchmarkResult, EvaluationRun
from infrastructure.persistence.models.evaluation import (
    BenchmarkResultModel,
    EvaluationRunModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLEvaluationRunRepository(BaseRepository[EvaluationRun, EvaluationRunModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvaluationRunModel)

    def _to_model(self, entity: EvaluationRun) -> EvaluationRunModel:
        return EvaluationRunModel(
            id=entity.id,
            run_type=entity.run_type,
            window_days=entity.window_days,
            agent_run_count=entity.agent_run_count,
            accuracy_score=entity.accuracy_score,
            precision_score=entity.precision_score,
            recall_score=entity.recall_score,
            confidence_score=entity.confidence_score,
            hallucination_rate=entity.hallucination_rate,
            error_rate=entity.error_rate,
            cost_usd_total=entity.cost_usd_total,
            cost_usd_last_7d=entity.cost_usd_last_7d,
            cost_usd_last_30d=entity.cost_usd_last_30d,
            benchmark_status=entity.benchmark_status,
            benchmark_passed=entity.benchmark_passed,
            benchmark_total=entity.benchmark_total,
            platform_health_score=entity.platform_health_score,
            raw_metrics=entity.raw_metrics,
            computed_at=entity.computed_at,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: EvaluationRunModel) -> EvaluationRun:
        return EvaluationRun(
            id=model.id,
            run_type=model.run_type,
            window_days=model.window_days,
            agent_run_count=model.agent_run_count,
            accuracy_score=model.accuracy_score,
            precision_score=model.precision_score,
            recall_score=model.recall_score,
            confidence_score=model.confidence_score,
            hallucination_rate=model.hallucination_rate,
            error_rate=model.error_rate,
            cost_usd_total=model.cost_usd_total,
            cost_usd_last_7d=model.cost_usd_last_7d,
            cost_usd_last_30d=model.cost_usd_last_30d,
            benchmark_status=model.benchmark_status,
            benchmark_passed=model.benchmark_passed,
            benchmark_total=model.benchmark_total,
            platform_health_score=model.platform_health_score,
            raw_metrics=model.raw_metrics or {},
            computed_at=model.computed_at,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_latest(self) -> EvaluationRun | None:
        stmt = (
            select(EvaluationRunModel)
            .order_by(EvaluationRunModel.computed_at.desc().nullslast())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_id(self, run_id: str) -> EvaluationRun | None:
        model = await self._session.get(EvaluationRunModel, run_id)
        return self._to_domain(model) if model else None

    async def list_recent(self, limit: int = 12) -> list[EvaluationRun]:
        stmt = (
            select(EvaluationRunModel)
            .order_by(EvaluationRunModel.computed_at.desc().nullslast())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]


class SQLBenchmarkResultRepository(
    BaseRepository[BenchmarkResult, BenchmarkResultModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BenchmarkResultModel)

    def _to_model(self, entity: BenchmarkResult) -> BenchmarkResultModel:
        return BenchmarkResultModel(
            id=entity.id,
            evaluation_run_id=entity.evaluation_run_id,
            benchmark_name=entity.benchmark_name,
            module=entity.module,
            dimension=entity.dimension,
            passed=entity.passed,
            score=entity.score,
            expected_output=entity.expected_output,
            actual_output=entity.actual_output,
            failure_reason=entity.failure_reason,
            duration_ms=entity.duration_ms,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: BenchmarkResultModel) -> BenchmarkResult:
        return BenchmarkResult(
            id=model.id,
            evaluation_run_id=model.evaluation_run_id,
            benchmark_name=model.benchmark_name,
            module=model.module,
            dimension=model.dimension,
            passed=model.passed,
            score=model.score,
            expected_output=model.expected_output,
            actual_output=model.actual_output,
            failure_reason=model.failure_reason,
            duration_ms=model.duration_ms,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_run(self, evaluation_run_id: str) -> list[BenchmarkResult]:
        stmt = (
            select(BenchmarkResultModel)
            .where(BenchmarkResultModel.evaluation_run_id == evaluation_run_id)
            .order_by(BenchmarkResultModel.module, BenchmarkResultModel.benchmark_name)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_by_run_ids(self, run_ids: list[str]) -> list[BenchmarkResult]:
        if not run_ids:
            return []
        stmt = (
            select(BenchmarkResultModel)
            .where(BenchmarkResultModel.evaluation_run_id.in_(run_ids))
            .order_by(BenchmarkResultModel.module, BenchmarkResultModel.evaluation_run_id)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
