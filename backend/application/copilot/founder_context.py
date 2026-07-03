"""Founder Chat context assembler (GAP-04).

Collects internal EIOS platform metrics — evaluation runs, benchmark results,
agent monitoring, recent errors — and serialises them into a compact JSON
snapshot for the Founder Chat system prompt.

No ESG / supplier / organisational data is included here — the Founder Chat
answers exclusively about platform health, not about any customer's supply chain.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.agent_run import AgentRunModel
from infrastructure.persistence.repositories.evaluation import (
    SQLBenchmarkResultRepository,
    SQLEvaluationRunRepository,
)


async def build_founder_context(session: AsyncSession, *, window_days: int = 30) -> str:
    """Return a JSON string with current platform health metrics.

    Always returns a valid JSON string even when no evaluation data exists.
    The caller embeds this into the LLM system prompt.
    """
    run_repo = SQLEvaluationRunRepository(session)
    bm_repo = SQLBenchmarkResultRepository(session)

    latest = await run_repo.get_latest()
    trends = await run_repo.list_recent(limit=6)

    snapshot: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "window_days": window_days,
        "platform_health": None,
        "latest_evaluation": None,
        "trend_accuracy": [],
        "trend_confidence": [],
        "trend_hallucination_rate": [],
        "trend_cost_usd": [],
        "benchmark_suite": [],
        "agent_monitoring": {},
        "recent_agent_errors": [],
    }

    # ── Latest evaluation run ─────────────────────────────────────────────────

    if latest is not None:
        snapshot["platform_health"] = {
            "score": latest.platform_health_score,
            "benchmark_status": latest.benchmark_status,
            "benchmark_passed": latest.benchmark_passed,
            "benchmark_total": latest.benchmark_total,
            "accuracy": latest.accuracy_score,
            "confidence": latest.confidence_score,
            "hallucination_rate": latest.hallucination_rate,
            "error_rate": latest.error_rate,
            "cost_usd_last_7d": latest.cost_usd_last_7d,
            "cost_usd_last_30d": latest.cost_usd_last_30d,
            "agent_run_count": latest.agent_run_count,
            "computed_at": latest.computed_at.isoformat() if latest.computed_at else None,
        }
        snapshot["latest_evaluation"] = snapshot["platform_health"]

        # Benchmark details
        bm_results = await bm_repo.list_by_run(latest.id)
        snapshot["benchmark_suite"] = [
            {
                "name": b.benchmark_name,
                "module": b.module,
                "passed": b.passed,
                "score": b.score,
                "failure_reason": b.failure_reason or None,
            }
            for b in bm_results
        ]

    # ── Trend series ──────────────────────────────────────────────────────────

    for run in reversed(trends):
        dt = run.computed_at.isoformat() if run.computed_at else run.created_at.isoformat()
        snapshot["trend_accuracy"].append({"at": dt, "value": run.accuracy_score})
        snapshot["trend_confidence"].append({"at": dt, "value": run.confidence_score})
        snapshot["trend_hallucination_rate"].append({"at": dt, "value": run.hallucination_rate})
        snapshot["trend_cost_usd"].append({"at": dt, "value": run.cost_usd_last_30d})

    # ── Agent monitoring summary ──────────────────────────────────────────────

    try:
        from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

        stmt = select(
            MonitoringAgentModel.status, func.count().label("n")
        ).group_by(MonitoringAgentModel.status)
        result = await session.execute(stmt)
        counts = {row.status: row.n for row in result.all()}
        snapshot["agent_monitoring"] = {
            "active": counts.get("ACTIVE", 0),
            "idle": counts.get("IDLE", 0),
            "error": counts.get("ERROR", 0),
            "disabled": counts.get("DISABLED", 0),
            "total": sum(counts.values()),
        }
    except Exception:
        pass

    # ── Recent agent errors (last 7 days, limit 10) ───────────────────────────

    try:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        err_stmt = (
            select(
                AgentRunModel.id,
                AgentRunModel.agent_type,
                AgentRunModel.error,
                AgentRunModel.created_at,
                AgentRunModel.confidence,
            )
            .where(AgentRunModel.error.isnot(None), AgentRunModel.created_at >= cutoff)
            .order_by(AgentRunModel.created_at.desc())
            .limit(10)
        )
        err_rows = (await session.execute(err_stmt)).all()
        snapshot["recent_agent_errors"] = [
            {
                "agent_type": r.agent_type,
                "error_summary": (r.error or "")[:120],
                "at": r.created_at.isoformat() if r.created_at else None,
                "confidence": r.confidence,
            }
            for r in err_rows
        ]
    except Exception:
        pass

    return json.dumps(snapshot, ensure_ascii=False, default=str)
