"""EIOS Evaluation Engine (GAP-02 / FR-014).

Deterministic, auditable, reproducible — no LLM calls.
Computes platform quality metrics from AgentRunModel records
and runs a built-in benchmark suite against EIOS deterministic modules.

Outputs:
  - EvaluationRun: aggregated quality snapshot
  - list[BenchmarkResult]: per-test-case pass/fail details

Token pricing (USD per 1M tokens, as of 2026-07):
  claude-sonnet-*: input $3.00 / output $15.00
  claude-opus-*:   input $15.00 / output $75.00
  claude-haiku-*:  input $0.80 / output $4.00
  gpt-4o*:         input $2.50 / output $10.00
  default:         input $3.00 / output $15.00
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.evaluation import BenchmarkResult, EvaluationRun
from infrastructure.persistence.models.agent_run import AgentRunModel

# ── Token pricing ─────────────────────────────────────────────────────────────

_PRICING: list[tuple[str, float, float]] = [
    # (prefix, input_per_1M, output_per_1M)
    ("claude-opus", 15.00, 75.00),
    ("claude-haiku", 0.80, 4.00),
    ("claude-sonnet", 3.00, 15.00),
    ("claude-fable", 3.00, 15.00),
    ("gpt-4o-mini", 0.15, 0.60),
    ("gpt-4o", 2.50, 10.00),
]
_DEFAULT_PRICE = (3.00, 15.00)


def _token_cost(model: str | None, input_tokens: int, output_tokens: int) -> float:
    m = (model or "").lower()
    for prefix, inp, out in _PRICING:
        if m.startswith(prefix):
            return (input_tokens * inp + output_tokens * out) / 1_000_000
    inp, out = _DEFAULT_PRICE
    return (input_tokens * inp + output_tokens * out) / 1_000_000


# ── Benchmark suite ───────────────────────────────────────────────────────────
# Each case: (name, module, dimension, run_fn) where run_fn() → (passed, score, expected, actual)


def _bm_credibility_high() -> tuple[bool, float, str, str]:
    from application.intelligence_engine.source_credibility import get_credibility

    r = get_credibility("eu_sanctions")  # official EU sanctions registry → High
    expected = "High"
    passed = r.level == expected
    return passed, 1.0 if passed else 0.0, expected, r.level


def _bm_credibility_low() -> tuple[bool, float, str, str]:
    from application.intelligence_engine.source_credibility import get_credibility

    r = get_credibility("__completely_unknown_source_xyz__")  # unknown → Low (default)
    expected = "Low"
    passed = r.level == expected
    return passed, 1.0 if passed else 0.0, expected, r.level


def _bm_credibility_news() -> tuple[bool, float, str, str]:
    from application.intelligence_engine.source_credibility import get_credibility

    r = get_credibility("gdelt_news")  # GDELT news feed → Low (raw news)
    expected = "Low"
    passed = r.level == expected
    return passed, 1.0 if passed else 0.0, expected, r.level


def _bm_prio_ordering() -> tuple[bool, float, str, str]:
    from application.due_diligence.prioritization_engine import compute_prioritization

    suppliers = [
        {"id": "s1", "name": "Alpha", "supplier_tier": "Tier 1"},
        {"id": "s2", "name": "Beta", "supplier_tier": "Tier 1"},
        {"id": "s3", "name": "Gamma", "supplier_tier": "Tier 1"},
    ]
    scores = {
        "s1": {"risk_band": "Critical", "risk_score": 90},
        "s2": {"risk_band": "High", "risk_score": 60},
        "s3": {"risk_band": "Low", "risk_score": 5},
    }
    result = compute_prioritization(
        organization_id="test",
        suppliers=suppliers,
        supplier_scores=scores,
        finding_counts={},
    )
    expected = "s1,s2,s3"
    actual = ",".join(r["supplier_id"] for r in result)
    passed = actual == expected
    return passed, 1.0 if passed else 0.0, expected, actual


def _bm_prio_severity_weight() -> tuple[bool, float, str, str]:
    from application.due_diligence.prioritization_engine import compute_prioritization

    suppliers = [{"id": "x", "name": "X", "supplier_tier": "Tier 1"}]
    scores = {"x": {"risk_band": "Critical", "risk_score": 100}}
    result = compute_prioritization(
        organization_id="test",
        suppliers=suppliers,
        supplier_scores=scores,
        finding_counts={"x": 15},
    )
    score = result[0]["priority_score"]
    # Critical(4)*0.40 + 4.0*0.35 + 4.0*0.25 = 4.0; tier_factor=1.0 → 4.0
    expected = "4.0000"
    actual = f"{score:.4f}"
    passed = abs(score - 4.0) < 0.0001
    return passed, 1.0 if passed else 0.0, expected, actual


def _bm_lksg_sections() -> tuple[bool, float, str, str]:
    from application.due_diligence.lksg_statement_engine import build_lksg_statement

    result = build_lksg_statement(
        organization_id="test",
        organization_name="Test GmbH",
        reporting_year=2025,
        suppliers=[],
        supplier_scores={},
        findings=[],
        risks=[],
        recommendations=[],
        compliance_gaps=[],
        controls=[],
        evidence_items=[],
        grievances=[],
    )
    sections = [k for k in result if k.startswith("section_")]
    expected = "6"
    actual = str(len(sections))
    passed = len(sections) == 6
    return passed, 1.0 if passed else 0.0, expected, actual


def _bm_impact_summary_format() -> tuple[bool, float, str, str]:
    from application.regulatory.change_scanner import build_impact_summary

    result = build_impact_summary(
        framework_code="CSDDD",
        assessment_count=3,
        gap_count=1,
        affected_sectors=["13", "14"],
    )
    expected = "non-empty string containing 'CSDDD'"
    actual = result[:60]
    passed = "CSDDD" in result and len(result) > 10
    return passed, 1.0 if passed else 0.0, expected, actual


def _bm_regulatory_seed_count() -> tuple[bool, float, str, str]:
    from application.regulatory.change_scanner import REGULATORY_CHANGE_SEED

    expected = "5"
    actual = str(len(REGULATORY_CHANGE_SEED))
    passed = len(REGULATORY_CHANGE_SEED) >= 5
    return passed, 1.0 if passed else 0.0, expected, actual


_BENCHMARK_SUITE: list[tuple[str, str, str, object]] = [
    ("CREDIBILITY_HIGH_SOURCE", "source_credibility", "accuracy", _bm_credibility_high),
    ("CREDIBILITY_LOW_SOURCE", "source_credibility", "accuracy", _bm_credibility_low),
    ("CREDIBILITY_NEWS_AGENCY", "source_credibility", "accuracy", _bm_credibility_news),
    ("PRIORITIZATION_ORDERING", "prioritization", "accuracy", _bm_prio_ordering),
    ("PRIORITIZATION_MAX_SCORE", "prioritization", "accuracy", _bm_prio_severity_weight),
    ("LKSG_STATEMENT_SECTIONS", "lksg_statement", "accuracy", _bm_lksg_sections),
    ("IMPACT_SUMMARY_FORMAT", "regulatory_changes", "accuracy", _bm_impact_summary_format),
    ("REGULATORY_SEED_COUNT", "regulatory_changes", "accuracy", _bm_regulatory_seed_count),
]


def _run_benchmarks(evaluation_run_id: str, now: datetime) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    for name, module, dimension, fn in _BENCHMARK_SUITE:
        t0 = time.perf_counter()
        try:
            passed, score, expected, actual = fn()
            failure_reason = "" if passed else f"Expected '{expected}', got '{actual}'"
        except Exception as exc:
            passed, score, expected, actual = False, 0.0, "no exception", str(exc)[:200]
            failure_reason = f"Exception: {exc}"
        duration_ms = (time.perf_counter() - t0) * 1000

        results.append(
            BenchmarkResult(
                evaluation_run_id=evaluation_run_id,
                benchmark_name=name,
                module=module,
                dimension=dimension,
                passed=passed,
                score=score,
                expected_output=expected,
                actual_output=actual,
                failure_reason=failure_reason,
                duration_ms=round(duration_ms, 2),
                status=EntityStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
    return results


# ── Live metric computation ───────────────────────────────────────────────────


async def _compute_live_metrics(session: AsyncSession, window_days: int) -> dict:
    """Query agent_runs for the evaluation window and compute quality metrics."""
    now = datetime.now(UTC)
    cutoff_all = now - timedelta(days=window_days)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # All runs in window
    stmt = select(
        AgentRunModel.confidence,
        AgentRunModel.error,
        AgentRunModel.input_tokens,
        AgentRunModel.output_tokens,
        AgentRunModel.llm_model,
        AgentRunModel.created_at,
    ).where(AgentRunModel.created_at >= cutoff_all)
    result = await session.execute(stmt)
    rows = result.all()

    total = len(rows)
    if total == 0:
        return {
            "agent_run_count": 0,
            "confidence_score": 0.0,
            "error_rate": 0.0,
            "hallucination_rate": 0.0,
            "cost_usd_total": 0.0,
            "cost_usd_last_7d": 0.0,
            "cost_usd_last_30d": 0.0,
            "by_agent_type": {},
        }

    errors = sum(1 for r in rows if r.error)
    confidences = [r.confidence for r in rows if r.confidence is not None]
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Hallucination proxy: runs where confidence > 0.8 AND error is set
    # (overconfident but wrong)
    high_conf_errors = sum(1 for r in rows if r.error and (r.confidence or 0) > 0.8)
    hallucination_rate = high_conf_errors / total if total else 0.0

    # Cost
    def cost_for_rows(rs) -> float:
        return sum(_token_cost(r.llm_model, r.input_tokens or 0, r.output_tokens or 0) for r in rs)

    total_cost = cost_for_rows(rows)
    cost_7d = cost_for_rows(r for r in rows if r.created_at and r.created_at >= cutoff_7d)
    cost_30d = cost_for_rows(r for r in rows if r.created_at and r.created_at >= cutoff_30d)

    return {
        "agent_run_count": total,
        "confidence_score": round(mean_confidence, 4),
        "error_rate": round(errors / total, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "cost_usd_total": round(total_cost, 6),
        "cost_usd_last_7d": round(cost_7d, 6),
        "cost_usd_last_30d": round(cost_30d, 6),
    }


# ── Public entry point ────────────────────────────────────────────────────────


async def run_evaluation(
    session: AsyncSession,
    *,
    run_type: str = "manual",
    window_days: int = 30,
    triggered_by: str = "",
) -> tuple[EvaluationRun, list[BenchmarkResult]]:
    """Run a full evaluation cycle.

    Steps:
    1. Query live metrics from agent_runs.
    2. Run deterministic benchmark suite.
    3. Assemble EvaluationRun + BenchmarkResult domain objects (not persisted here —
       caller persists them via repositories).

    Returns (evaluation_run, benchmark_results).
    """
    now = datetime.now(UTC)

    # 1 — Live metrics
    live = await _compute_live_metrics(session, window_days)

    # 2 — Benchmarks
    from uuid import uuid4

    run_id = str(uuid4())
    bm_results = _run_benchmarks(run_id, now)

    bm_passed = sum(1 for b in bm_results if b.passed)
    bm_total = len(bm_results)
    accuracy = bm_passed / bm_total if bm_total else 0.0

    # Precision = accuracy (we treat each benchmark as true-positive detection)
    # Recall = accuracy (all benchmark cases in scope are run)
    # For a real system these would differ; benchmarks are the ground truth here.
    precision = accuracy
    recall = accuracy

    # Benchmark status thresholds
    if accuracy >= 0.90:
        bm_status = "green"
    elif accuracy >= 0.70:
        bm_status = "yellow"
    else:
        bm_status = "red"

    # Platform health score (0–100):
    # 40% benchmark accuracy + 30% confidence + 20% (1 - error_rate) + 10% (1 - hallucination)
    health = (
        accuracy * 0.40
        + live["confidence_score"] * 0.30
        + (1.0 - live["error_rate"]) * 0.20
        + (1.0 - live["hallucination_rate"]) * 0.10
    ) * 100

    evaluation_run = EvaluationRun(
        id=run_id,
        run_type=run_type,
        window_days=window_days,
        agent_run_count=live["agent_run_count"],
        accuracy_score=round(accuracy, 4),
        precision_score=round(precision, 4),
        recall_score=round(recall, 4),
        confidence_score=live["confidence_score"],
        hallucination_rate=live["hallucination_rate"],
        error_rate=live["error_rate"],
        cost_usd_total=live["cost_usd_total"],
        cost_usd_last_7d=live["cost_usd_last_7d"],
        cost_usd_last_30d=live["cost_usd_last_30d"],
        benchmark_status=bm_status,
        benchmark_passed=bm_passed,
        benchmark_total=bm_total,
        platform_health_score=round(health, 2),
        computed_at=now,
        status=EntityStatus.ACTIVE,
        created_by=triggered_by,
        created_at=now,
        updated_at=now,
        raw_metrics={
            "live": live,
            "benchmark_pass_rate": round(accuracy, 4),
            "benchmark_cases": bm_total,
        },
    )

    # Assign run_id to benchmark results
    for b in bm_results:
        b.evaluation_run_id = run_id
        b.created_by = triggered_by

    return evaluation_run, bm_results
