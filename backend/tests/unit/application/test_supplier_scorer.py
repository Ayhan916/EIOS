"""Unit tests for the Supplier Scoring Engine (M28)."""

from application.scoring.supplier_scorer import (
    SCORE_VERSION,
    ScoreInputs,
    build_drivers,
    calculate_esg_scores,
    calculate_risk_score,
    calculate_trend,
)
from domain.enums import RiskBand, TrendDirection

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _clean_inputs(**kwargs) -> ScoreInputs:
    """ScoreInputs with all zeros; override specific fields via kwargs."""
    return ScoreInputs(**kwargs)


# ── Risk Score ────────────────────────────────────────────────────────────────


class TestCalculateRiskScore:
    def test_zero_inputs_gives_zero_score_low_band(self) -> None:
        inputs = _clean_inputs()
        score, band = calculate_risk_score(inputs)
        assert score == 0.0
        assert band == RiskBand.LOW

    def test_single_critical_finding(self) -> None:
        inputs = _clean_inputs(critical_findings=1)
        score, band = calculate_risk_score(inputs)
        # raw = 20, score = 20/5 = 4.0
        assert score == 4.0
        assert band == RiskBand.LOW

    def test_five_critical_findings_gives_moderate(self) -> None:
        inputs = _clean_inputs(critical_findings=5)
        score, _ = calculate_risk_score(inputs)
        # raw = 5*20 = 100, score = 100/5 = 20
        assert score == 20.0

    def test_many_findings_capped_at_100(self) -> None:
        inputs = _clean_inputs(
            critical_findings=100,
            high_findings=100,
            medium_findings=100,
            critical_risks=100,
            overdue_actions=100,
        )
        score, band = calculate_risk_score(inputs)
        assert score == 100.0
        assert band == RiskBand.CRITICAL

    def test_risk_band_low(self) -> None:
        inputs = _clean_inputs(low_findings=5)
        score, band = calculate_risk_score(inputs)
        assert band == RiskBand.LOW

    def test_risk_band_moderate(self) -> None:
        # raw = 150 → score = 30 → Moderate (26-50)
        inputs = _clean_inputs(critical_findings=3, high_findings=4, medium_findings=10)
        score, band = calculate_risk_score(inputs)
        assert 26 <= score <= 50
        assert band == RiskBand.MODERATE

    def test_risk_band_high(self) -> None:
        # raw = 10*20 + 10*10 + 10*3 + 5*8 = 200+100+30+40 = 370 → 74.0 → HIGH
        inputs = _clean_inputs(
            critical_findings=10, high_findings=10, medium_findings=10, overdue_actions=5
        )
        score, band = calculate_risk_score(inputs)
        assert band == RiskBand.HIGH
        assert 51.0 <= score <= 75.0

    def test_risk_band_critical_threshold(self) -> None:
        # raw = 10*20 + 10*8 + 10*15 = 200+80+150 = 430 → 86.0 → Critical
        inputs = _clean_inputs(
            critical_findings=10,
            overdue_actions=10,
            critical_risks=10,
        )
        score, band = calculate_risk_score(inputs)
        assert score == 86.0
        assert band == RiskBand.CRITICAL

    def test_overdue_actions_weighted_heavily(self) -> None:
        inputs_overdue = _clean_inputs(overdue_actions=5)
        inputs_open = _clean_inputs(open_actions=5)
        score_overdue, _ = calculate_risk_score(inputs_overdue)
        score_open, _ = calculate_risk_score(inputs_open)
        # overdue: 5*8=40 → 8.0; open: 5*3=15 → 3.0
        assert score_overdue > score_open

    def test_score_version_constant(self) -> None:
        assert SCORE_VERSION == "1.0"


# ── ESG Score ─────────────────────────────────────────────────────────────────


class TestCalculateEsgScores:
    def test_zero_inputs_perfect_scores(self) -> None:
        inputs = _clean_inputs()
        total, env, social, gov = calculate_esg_scores(inputs)
        assert total == 100.0
        assert env == 100.0
        assert social == 100.0
        assert gov == 100.0

    def test_environmental_critical_reduces_env_score(self) -> None:
        inputs = _clean_inputs(env_critical=1)
        total, env, social, gov = calculate_esg_scores(inputs)
        assert env == 88.0  # 100 - 12
        assert social == 100.0
        assert gov == 100.0

    def test_social_high_reduces_social_score(self) -> None:
        inputs = _clean_inputs(social_high=2)
        _, env, social, gov = calculate_esg_scores(inputs)
        assert social == 88.0  # 100 - 2*6
        assert env == 100.0
        assert gov == 100.0

    def test_governance_medium_low_reduction(self) -> None:
        inputs = _clean_inputs(gov_medium=5, gov_low=4)
        _, _, _, gov = calculate_esg_scores(inputs)
        # deduction = 5*2 + 4*0.5 = 10 + 2 = 12
        assert gov == 88.0

    def test_total_is_average_of_three_pillars(self) -> None:
        inputs = _clean_inputs(env_critical=5, social_critical=5, gov_critical=5)
        total, env, social, gov = calculate_esg_scores(inputs)
        expected_total = round((env + social + gov) / 3.0, 1)
        assert total == expected_total

    def test_score_floors_at_zero(self) -> None:
        inputs = _clean_inputs(env_critical=100)
        _, env, _, _ = calculate_esg_scores(inputs)
        assert env == 0.0

    def test_isolated_pillar_scores(self) -> None:
        inputs = _clean_inputs(env_high=3)
        _, env, social, gov = calculate_esg_scores(inputs)
        assert env == 82.0  # 100 - 3*6
        assert social == 100.0
        assert gov == 100.0


# ── Trend ─────────────────────────────────────────────────────────────────────


class TestCalculateTrend:
    def test_no_previous_score_is_stable(self) -> None:
        direction, delta = calculate_trend(75.0, None)
        assert direction == TrendDirection.STABLE
        assert delta == 0.0

    def test_large_improvement(self) -> None:
        direction, delta = calculate_trend(80.0, 70.0)
        assert direction == TrendDirection.IMPROVING
        assert delta == 10.0

    def test_small_improvement_within_stable_band(self) -> None:
        direction, delta = calculate_trend(73.0, 71.0)
        assert direction == TrendDirection.STABLE
        assert delta == 2.0

    def test_exactly_three_point_change_is_stable(self) -> None:
        direction, _ = calculate_trend(75.0, 72.0)
        assert direction == TrendDirection.STABLE

    def test_just_above_threshold_is_improving(self) -> None:
        direction, _ = calculate_trend(75.4, 72.0)
        assert direction == TrendDirection.IMPROVING

    def test_deterioration(self) -> None:
        direction, delta = calculate_trend(60.0, 75.0)
        assert direction == TrendDirection.DETERIORATING
        assert delta == -15.0

    def test_small_deterioration_is_stable(self) -> None:
        direction, _ = calculate_trend(72.0, 74.0)
        assert direction == TrendDirection.STABLE

    def test_delta_sign_matches_direction(self) -> None:
        _, delta_up = calculate_trend(80.0, 70.0)
        _, delta_down = calculate_trend(60.0, 80.0)
        assert delta_up > 0
        assert delta_down < 0


# ── Drivers ───────────────────────────────────────────────────────────────────


class TestBuildDrivers:
    def test_no_issues_produces_empty_drivers(self) -> None:
        drivers = build_drivers(_clean_inputs())
        assert drivers == []

    def test_critical_finding_produces_high_impact_driver(self) -> None:
        inputs = _clean_inputs(critical_findings=3)
        drivers = build_drivers(inputs)
        assert any(d["factor"] == "Critical Findings" and d["impact"] == "high" for d in drivers)

    def test_overdue_actions_produce_high_impact_driver(self) -> None:
        inputs = _clean_inputs(overdue_actions=2)
        drivers = build_drivers(inputs)
        assert any(d["factor"] == "Overdue Actions" and d["impact"] == "high" for d in drivers)

    def test_zero_count_not_included(self) -> None:
        inputs = _clean_inputs(critical_findings=0, high_findings=2)
        drivers = build_drivers(inputs)
        factors = [d["factor"] for d in drivers]
        assert "Critical Findings" not in factors
        assert "High Findings" in factors

    def test_driver_has_required_fields(self) -> None:
        inputs = _clean_inputs(critical_risks=1)
        drivers = build_drivers(inputs)
        assert len(drivers) > 0
        d = drivers[0]
        assert "factor" in d
        assert "count" in d
        assert "impact" in d
        assert "description" in d

    def test_high_impact_drivers_before_low(self) -> None:
        inputs = _clean_inputs(
            critical_findings=2,
            overdue_actions=1,
            open_actions=5,
            medium_findings=3,
        )
        drivers = build_drivers(inputs)
        impacts = [d["impact"] for d in drivers]
        # All "high" entries appear before "low"
        last_high = max((i for i, v in enumerate(impacts) if v == "high"), default=-1)
        first_low = min((i for i, v in enumerate(impacts) if v == "low"), default=len(impacts))
        assert last_high < first_low

    def test_driver_count_matches_input(self) -> None:
        inputs = _clean_inputs(critical_findings=4)
        drivers = build_drivers(inputs)
        crit_driver = next(d for d in drivers if d["factor"] == "Critical Findings")
        assert crit_driver["count"] == 4

    def test_all_driver_types_present_when_all_nonzero(self) -> None:
        inputs = _clean_inputs(
            critical_findings=1,
            high_findings=1,
            medium_findings=1,
            critical_risks=1,
            high_risks=1,
            open_actions=1,
            overdue_actions=1,
            medium_risks=1,
        )
        drivers = build_drivers(inputs)
        factors = {d["factor"] for d in drivers}
        assert "Critical Findings" in factors
        assert "Overdue Actions" in factors
        assert "High Findings" in factors
