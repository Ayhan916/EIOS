"""Deterministic weakness detector and improvement proposal generator (GAP-05).

Rules (all deterministic, auditable, no LLM):

Weakness types and thresholds:
  LOW_BENCHMARK_ACCURACY   module pass_rate < 1.0         → fix benchmark/module
  DECLINING_ACCURACY_TREND accuracy drop ≥ 0.05 in last 3 → investigate regression
  HIGH_HALLUCINATION_RATE  hallucination_rate > 0.05      → model calibration
  HIGH_ERROR_RATE          error_rate > 0.10              → agent stability
  LOW_CONFIDENCE           confidence_score < 0.70        → data quality / prompts
  LOW_PLATFORM_HEALTH      platform_health_score < 70     → combined intervention
  COST_ANOMALY             cost_usd_last_7d > cost_usd_last_30d * 0.40  → audit

Priority score formula (0–10):
  Computed from severity × expected_impact
  Severity multipliers:
    critical (red):   3.0
    high (yellow):    2.0
    moderate:         1.0

Agents MUST NOT auto-approve proposals — only human API calls may change status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from domain.enums import EntityStatus
from domain.evaluation import BenchmarkResult, EvaluationRun
from domain.improvement import ImprovementProposal

# ── Thresholds ────────────────────────────────────────────────────────────────

_BM_ACCURACY_THRESHOLD = 1.0  # 100% pass rate expected per module
_HALLUCINATION_WARN = 0.05  # 5%
_ERROR_RATE_WARN = 0.10  # 10%
_CONFIDENCE_WARN = 0.70  # 70%
_HEALTH_WARN = 70.0  # /100
_ACCURACY_DROP_WARN = 0.05  # 5 pp drop over 3 runs
_COST_WEEK_RATIO_WARN = 0.40  # weekly cost > 40% of monthly → spike


# ── Improvement proposal catalogue ───────────────────────────────────────────


def _proposal(
    *,
    weakness_type: str,
    affected_module: str,
    current_value: float,
    target_value: float,
    expected_impact: float,
    priority_score: float,
    title: str,
    description: str,
    suggested_action: str,
    before_run_id: str | None,
    now: datetime,
) -> ImprovementProposal:
    return ImprovementProposal(
        id=str(uuid4()),
        weakness_type=weakness_type,
        affected_module=affected_module,
        current_value=round(current_value, 4),
        target_value=round(target_value, 4),
        expected_impact=round(expected_impact, 4),
        priority_score=round(priority_score, 2),
        title=title,
        description=description,
        suggested_action=suggested_action,
        approval_status="DRAFT",
        before_evaluation_run_id=before_run_id,
        status=EntityStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


# ── Main detector ─────────────────────────────────────────────────────────────


def detect_weaknesses(
    latest: EvaluationRun,
    bm_results: list[BenchmarkResult],
    trends: list[EvaluationRun],
) -> list[ImprovementProposal]:
    """Deterministically detect platform weaknesses and return ranked proposals.

    All logic is rule-based. No LLM calls. Each proposal maps one weakness to
    one concrete suggested action.

    Args:
        latest: Most recent EvaluationRun.
        bm_results: BenchmarkResults for `latest`.
        trends: Recent EvaluationRuns in ascending time order (oldest first).

    Returns:
        List of ImprovementProposal in descending priority order.
    """
    now = datetime.now(UTC)
    proposals: list[ImprovementProposal] = []
    run_id = latest.id

    # ── 1. Low benchmark accuracy per module ─────────────────────────────────
    by_module: dict[str, list[BenchmarkResult]] = {}
    for b in bm_results:
        by_module.setdefault(b.module, []).append(b)

    for module, results in by_module.items():
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        pass_rate = passed / total if total else 1.0
        if pass_rate < _BM_ACCURACY_THRESHOLD:
            failed = [r for r in results if not r.passed]
            failure_names = ", ".join(r.benchmark_name for r in failed[:3])
            expected_impact = _BM_ACCURACY_THRESHOLD - pass_rate
            # Priority: bigger gap = higher score; max 8
            priority = min(8.0, expected_impact * 20)
            proposals.append(
                _proposal(
                    weakness_type="LOW_BENCHMARK_ACCURACY",
                    affected_module=module,
                    current_value=pass_rate,
                    target_value=_BM_ACCURACY_THRESHOLD,
                    expected_impact=expected_impact,
                    priority_score=priority,
                    title=f"Benchmark failures in module '{module}' ({passed}/{total} passed)",
                    description=(
                        f"The benchmark suite for module '{module}' is not passing at 100%. "
                        f"Failing tests: {failure_names}. "
                        f"This indicates either a regression in the module implementation "
                        f"or an incorrect benchmark expectation."
                    ),
                    suggested_action=(
                        f"1. Review the failing benchmark definitions for '{module}'.\n"
                        f"2. Check for recent changes in the corresponding module implementation.\n"
                        f"3. Fix the root cause (code regression or stale benchmark expectation).\n"
                        f"4. Re-run evaluation to verify improvement."
                    ),
                    before_run_id=run_id,
                    now=now,
                )
            )

    # ── 2. Declining accuracy trend ──────────────────────────────────────────
    if len(trends) >= 3:
        recent = trends[-3:]  # oldest of the 3 to newest
        oldest_acc = recent[0].accuracy_score
        newest_acc = recent[-1].accuracy_score
        drop = oldest_acc - newest_acc
        if drop >= _ACCURACY_DROP_WARN:
            priority = min(9.0, drop * 40)
            proposals.append(
                _proposal(
                    weakness_type="DECLINING_ACCURACY_TREND",
                    affected_module="global",
                    current_value=newest_acc,
                    target_value=oldest_acc,
                    expected_impact=drop,
                    priority_score=priority,
                    title=f"Accuracy declining: {oldest_acc:.1%} → {newest_acc:.1%} over last 3 evaluations",
                    description=(
                        f"Platform benchmark accuracy has dropped by {drop:.1%} over the last 3 evaluation runs. "
                        f"This trend indicates a regression that may affect prediction quality across all modules."
                    ),
                    suggested_action=(
                        "1. Compare benchmark results between the last passing and first failing run.\n"
                        "2. Check for recent code or model changes that may have introduced a regression.\n"
                        "3. Review any infrastructure or dependency updates since the last good run.\n"
                        "4. Roll back or fix the regression, then re-run evaluation."
                    ),
                    before_run_id=run_id,
                    now=now,
                )
            )

    # ── 3. High hallucination rate ────────────────────────────────────────────
    if latest.hallucination_rate > _HALLUCINATION_WARN:
        h = latest.hallucination_rate
        expected_impact = h - _HALLUCINATION_WARN
        priority = min(9.5, expected_impact * 30)
        proposals.append(
            _proposal(
                weakness_type="HIGH_HALLUCINATION_RATE",
                affected_module="global",
                current_value=h,
                target_value=_HALLUCINATION_WARN,
                expected_impact=expected_impact,
                priority_score=priority,
                title=f"Hallucination proxy elevated: {h:.2%} (threshold: {_HALLUCINATION_WARN:.0%})",
                description=(
                    f"The hallucination proxy (high-confidence errors / total runs) is {h:.2%}, "
                    f"above the {_HALLUCINATION_WARN:.0%} threshold. "
                    f"This means agents are frequently producing confident-but-wrong outputs."
                ),
                suggested_action=(
                    "1. Audit the agent runs where confidence > 0.8 and error is set — identify common patterns.\n"
                    "2. Consider adding retrieval guardrails or confidence calibration.\n"
                    "3. Review the system prompt for over-confident phrasing.\n"
                    "4. Implement output verification for high-confidence results."
                ),
                before_run_id=run_id,
                now=now,
            )
        )

    # ── 4. High error rate ────────────────────────────────────────────────────
    if latest.error_rate > _ERROR_RATE_WARN:
        e = latest.error_rate
        expected_impact = e - _ERROR_RATE_WARN
        priority = min(8.0, expected_impact * 25)
        proposals.append(
            _proposal(
                weakness_type="HIGH_ERROR_RATE",
                affected_module="global",
                current_value=e,
                target_value=_ERROR_RATE_WARN,
                expected_impact=expected_impact,
                priority_score=priority,
                title=f"Agent error rate elevated: {e:.2%} (threshold: {_ERROR_RATE_WARN:.0%})",
                description=(
                    f"Agent runs are failing with errors at a rate of {e:.2%}. "
                    f"This degrades data quality and may cascade into downstream risk assessments."
                ),
                suggested_action=(
                    "1. Query recent agent_runs WHERE error IS NOT NULL to find common error patterns.\n"
                    "2. Check for external API timeouts, quota limits, or schema changes.\n"
                    "3. Add retry logic or circuit breakers for unstable external dependencies.\n"
                    "4. Review agent configuration and update error handling."
                ),
                before_run_id=run_id,
                now=now,
            )
        )

    # ── 5. Low confidence ─────────────────────────────────────────────────────
    if latest.confidence_score < _CONFIDENCE_WARN and latest.agent_run_count > 0:
        c = latest.confidence_score
        expected_impact = _CONFIDENCE_WARN - c
        priority = min(7.0, expected_impact * 15)
        proposals.append(
            _proposal(
                weakness_type="LOW_CONFIDENCE",
                affected_module="global",
                current_value=c,
                target_value=_CONFIDENCE_WARN,
                expected_impact=expected_impact,
                priority_score=priority,
                title=f"Mean agent confidence low: {c:.1%} (target: {_CONFIDENCE_WARN:.0%})",
                description=(
                    f"The mean agent confidence score is {c:.1%}, below the {_CONFIDENCE_WARN:.0%} target. "
                    f"Low confidence typically indicates insufficient context, poor retrieval quality, "
                    f"or ambiguous input data."
                ),
                suggested_action=(
                    "1. Review context assembly — are retrievers returning enough relevant data?\n"
                    "2. Check retrieval window and scoring thresholds.\n"
                    "3. Consider expanding data sources or improving chunk quality for embeddings.\n"
                    "4. Audit recent agent runs with confidence < 0.5 for common patterns."
                ),
                before_run_id=run_id,
                now=now,
            )
        )

    # ── 6. Low overall platform health ───────────────────────────────────────
    if latest.platform_health_score < _HEALTH_WARN:
        h = latest.platform_health_score
        expected_impact = (_HEALTH_WARN - h) / 100
        priority = min(10.0, expected_impact * 30)
        proposals.append(
            _proposal(
                weakness_type="LOW_PLATFORM_HEALTH",
                affected_module="global",
                current_value=h,
                target_value=_HEALTH_WARN,
                expected_impact=expected_impact,
                priority_score=priority,
                title=f"Platform Health Score below threshold: {h:.0f}/100 (target: {_HEALTH_WARN:.0f})",
                description=(
                    f"The overall Platform Health Score is {h:.0f}/100, below the {_HEALTH_WARN:.0f} minimum. "
                    f"This composite score weighs accuracy (40%), confidence (30%), "
                    f"(1-error_rate) (20%), and (1-hallucination_rate) (10%)."
                ),
                suggested_action=(
                    "1. Address the highest-priority individual proposals listed above.\n"
                    "2. Re-run evaluation after each fix to track the health score recovery.\n"
                    "3. Set a target recovery timeline and assign responsibility for each fix."
                ),
                before_run_id=run_id,
                now=now,
            )
        )

    # ── 7. Cost spike ─────────────────────────────────────────────────────────
    if (
        latest.cost_usd_last_30d > 0
        and latest.cost_usd_last_7d > latest.cost_usd_last_30d * _COST_WEEK_RATIO_WARN
    ):
        weekly = latest.cost_usd_last_7d
        monthly = latest.cost_usd_last_30d
        expected_pct = weekly / monthly
        expected_impact = expected_pct - _COST_WEEK_RATIO_WARN
        priority = min(6.0, expected_impact * 10)
        proposals.append(
            _proposal(
                weakness_type="COST_ANOMALY",
                affected_module="global",
                current_value=weekly,
                target_value=monthly * _COST_WEEK_RATIO_WARN,
                expected_impact=expected_impact,
                priority_score=priority,
                title=f"Cost spike: 7d spend (${weekly:.4f}) > {_COST_WEEK_RATIO_WARN:.0%} of 30d (${monthly:.4f})",
                description=(
                    f"Weekly API cost (${weekly:.4f}) is {expected_pct:.0%} of the monthly total (${monthly:.4f}). "
                    f"A healthy weekly spend should not exceed {_COST_WEEK_RATIO_WARN:.0%} of the monthly total. "
                    f"This suggests a cost spike — likely a large batch run or model misconfiguration."
                ),
                suggested_action=(
                    "1. Query agent_runs for the last 7 days grouped by llm_model to find cost drivers.\n"
                    "2. Check if any batch jobs or scheduled tasks ran unexpectedly.\n"
                    "3. Consider switching cheaper models for lower-stakes tasks (Haiku vs Sonnet).\n"
                    "4. Set API cost budget alerts on your LLM provider."
                ),
                before_run_id=run_id,
                now=now,
            )
        )

    # Sort by priority descending
    proposals.sort(key=lambda p: p.priority_score, reverse=True)
    return proposals
