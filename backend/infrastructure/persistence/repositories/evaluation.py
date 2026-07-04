"""Repositories for EvaluationRun, BenchmarkResult, and CalibrationEvent."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.evaluation import BenchmarkResult, CalibrationEvent, EvaluationRun
from infrastructure.persistence.models.evaluation import (
    BenchmarkResultModel,
    CalibrationEventModel,
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


class SQLCalibrationEventRepository(
    BaseRepository[CalibrationEvent, CalibrationEventModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CalibrationEventModel)

    def _to_model(self, entity: CalibrationEvent) -> CalibrationEventModel:
        return CalibrationEventModel(
            id=entity.id,
            organization_id=entity.organization_id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            predicted_confidence=entity.predicted_confidence,
            actual_outcome=entity.actual_outcome,
            recorded_by=entity.recorded_by,
            recorded_at=entity.recorded_at,
            status=entity.status,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at or datetime.now(UTC),
            updated_at=entity.updated_at or datetime.now(UTC),
        )

    def _to_domain(self, model: CalibrationEventModel) -> CalibrationEvent:
        return CalibrationEvent(
            id=model.id,
            organization_id=model.organization_id,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            predicted_confidence=model.predicted_confidence,
            actual_outcome=model.actual_outcome,
            recorded_by=model.recorded_by,
            recorded_at=model.recorded_at,
            status=model.status,
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_org(self, organization_id: str) -> list[CalibrationEvent]:
        stmt = (
            select(CalibrationEventModel)
            .where(CalibrationEventModel.organization_id == organization_id)
            .order_by(CalibrationEventModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def compute_curve(self, organization_id: str) -> list[dict]:
        """Return per-confidence-level accuracy stats (deterministic, no LLM)."""
        events = await self.list_by_org(organization_id)

        buckets: dict[str, dict[str, int]] = defaultdict(
            lambda: {"confirmed": 0, "refuted": 0, "unknown": 0}
        )
        for ev in events:
            level = ev.predicted_confidence.lower()
            outcome = ev.actual_outcome.lower()
            if outcome in ("confirmed", "refuted", "unknown"):
                buckets[level][outcome] += 1

        rows = []
        for level in ("high", "medium", "low"):
            b = buckets.get(level, {"confirmed": 0, "refuted": 0, "unknown": 0})
            confirmed = b["confirmed"]
            refuted = b["refuted"]
            unknown = b["unknown"]
            total = confirmed + refuted + unknown
            decisive = confirmed + refuted
            accuracy = round(confirmed / decisive, 4) if decisive > 0 else None
            rows.append(
                {
                    "confidence_level": level,
                    "total": total,
                    "confirmed": confirmed,
                    "refuted": refuted,
                    "unknown": unknown,
                    "accuracy": accuracy,
                }
            )
        return rows
