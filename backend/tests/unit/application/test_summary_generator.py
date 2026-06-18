"""Unit tests for M29 Executive Summary Generator.

All tests verify determinism: same inputs → same output, always.
"""

import pytest

from application.executive.summary_generator import (
    ExecutiveSummaryInputs,
    generate_executive_summary,
)


def _inputs(**kwargs) -> ExecutiveSummaryInputs:
    defaults = {
        "total_suppliers": 10,
        "scored_suppliers": 10,
        "critical_risk_count": 0,
        "high_risk_count": 0,
        "moderate_risk_count": 5,
        "low_risk_count": 5,
        "improving_count": 2,
        "deteriorating_count": 1,
        "avg_esg_score": 72.0,
        "avg_risk_score": 38.0,
        "open_actions": 3,
        "overdue_actions": 0,
        "resolved_actions": 7,
        "assessments_awaiting_review": 0,
        "assessments_approved": 8,
        "critical_findings_total": 0,
    }
    defaults.update(kwargs)
    return ExecutiveSummaryInputs(**defaults)


# ── Determinism ───────────────────────────────────────────────────────────────


def test_deterministic_same_inputs_same_output():
    inp = _inputs()
    assert generate_executive_summary(inp) == generate_executive_summary(inp)


# ── Portfolio overview sentence ────────────────────────────────────────────────


def test_all_scored():
    s = generate_executive_summary(_inputs(total_suppliers=5, scored_suppliers=5))
    assert "5 active suppliers" in s
    assert "all of which have been assessed" in s


def test_partial_scored():
    s = generate_executive_summary(_inputs(total_suppliers=10, scored_suppliers=7))
    assert "7 have been assessed" in s
    assert "3 awaiting initial assessment" in s


def test_none_scored():
    s = generate_executive_summary(_inputs(total_suppliers=4, scored_suppliers=0))
    assert "No suppliers have been scored yet" in s


def test_single_supplier_no_plural():
    s = generate_executive_summary(_inputs(total_suppliers=1, scored_suppliers=1))
    assert "1 active supplier" in s
    assert "suppliers" not in s.split("all")[0]


# ── ESG performance sentence ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "score,label",
    [
        (90.0, "strong"),
        (85.0, "strong"),
        (75.0, "adequate"),
        (70.0, "adequate"),
        (60.0, "below expectations"),
        (55.0, "below expectations"),
        (40.0, "poor"),
        (0.0, "poor"),
    ],
)
def test_esg_quality_labels(score, label):
    s = generate_executive_summary(_inputs(avg_esg_score=score))
    assert label in s


def test_esg_score_formatted():
    s = generate_executive_summary(_inputs(avg_esg_score=72.456))
    assert "72.5/100" in s


def test_no_esg_score_omits_sentence():
    s = generate_executive_summary(_inputs(avg_esg_score=None))
    assert "/100" not in s


# ── Risk concentration sentence ───────────────────────────────────────────────


def test_no_high_risk():
    s = generate_executive_summary(
        _inputs(high_risk_count=0, critical_risk_count=0, scored_suppliers=10)
    )
    assert "No suppliers are currently classified as High or Critical risk" in s


def test_high_and_critical_percentage():
    s = generate_executive_summary(
        _inputs(high_risk_count=3, critical_risk_count=2, scored_suppliers=10)
    )
    assert "5 suppliers" in s
    assert "50%" in s
    assert "2 Criticals" in s


def test_single_critical_no_plural():
    s = generate_executive_summary(
        _inputs(high_risk_count=0, critical_risk_count=1, scored_suppliers=5)
    )
    assert "1 Critical" in s
    assert "Criticals" not in s


def test_high_only_no_critical_clause():
    s = generate_executive_summary(
        _inputs(high_risk_count=2, critical_risk_count=0, scored_suppliers=8)
    )
    assert "including" not in s


# ── Trend direction sentence ───────────────────────────────────────────────────


def test_more_deteriorating_than_improving():
    s = generate_executive_summary(
        _inputs(deteriorating_count=5, improving_count=2)
    )
    assert "Risk exposure is increasing" in s
    assert "5" in s


def test_more_improving_than_deteriorating():
    s = generate_executive_summary(
        _inputs(improving_count=6, deteriorating_count=1)
    )
    assert "Portfolio risk is improving" in s
    assert "6" in s


def test_stable_when_equal():
    s = generate_executive_summary(
        _inputs(improving_count=3, deteriorating_count=3, scored_suppliers=10)
    )
    assert "broadly stable" in s


def test_trend_omitted_when_no_scored_suppliers():
    s = generate_executive_summary(
        _inputs(scored_suppliers=0, improving_count=0, deteriorating_count=0)
    )
    assert "broadly stable" not in s
    assert "improving" not in s.lower() or "portfolio" not in s


# ── Geographic / sector concentration ─────────────────────────────────────────


def test_country_and_sector():
    s = generate_executive_summary(
        _inputs(top_risk_country="Germany", top_risk_sector="Automotive")
    )
    assert "Germany" in s
    assert "Automotive" in s


def test_country_only():
    s = generate_executive_summary(
        _inputs(top_risk_country="Brazil", top_risk_sector=None)
    )
    assert "Brazil" in s
    assert "sector" not in s


def test_no_geo_info_omitted():
    s = generate_executive_summary(
        _inputs(top_risk_country=None, top_risk_sector=None)
    )
    assert "concentration is in" not in s


# ── Action health sentence ────────────────────────────────────────────────────


def test_overdue_actions_mentioned():
    s = generate_executive_summary(_inputs(overdue_actions=4, open_actions=10))
    assert "4 actions are overdue" in s
    assert "10 total open" in s


def test_single_overdue_no_plural():
    s = generate_executive_summary(_inputs(overdue_actions=1, open_actions=5))
    assert "1 action is overdue" in s


def test_open_no_overdue():
    s = generate_executive_summary(_inputs(overdue_actions=0, open_actions=3))
    assert "3 actions are open with no items overdue" in s


def test_all_resolved():
    s = generate_executive_summary(_inputs(overdue_actions=0, open_actions=0))
    assert "All recommended actions have been resolved" in s


# ── Governance sentence ────────────────────────────────────────────────────────


def test_awaiting_review_included():
    s = generate_executive_summary(_inputs(assessments_awaiting_review=5))
    assert "5 assessments are awaiting governance review" in s


def test_none_awaiting_review_omitted():
    s = generate_executive_summary(_inputs(assessments_awaiting_review=0))
    assert "awaiting governance review" not in s


# ── Priority call-to-action ───────────────────────────────────────────────────


def test_cta_critical_takes_priority():
    s = generate_executive_summary(
        _inputs(
            critical_risk_count=2,
            overdue_actions=10,
            deteriorating_count=5,
            high_risk_count=3,
        )
    )
    assert "2 Critical risk suppliers" in s
    assert "prioritise" in s.lower()


def test_cta_overdue_when_no_critical():
    s = generate_executive_summary(
        _inputs(critical_risk_count=0, overdue_actions=3, deteriorating_count=0)
    )
    assert "closure of overdue" in s


def test_cta_deteriorating_when_no_critical_no_overdue():
    s = generate_executive_summary(
        _inputs(critical_risk_count=0, overdue_actions=0, deteriorating_count=4)
    )
    assert "deteriorating suppliers" in s


def test_cta_high_risk_when_no_other_triggers():
    s = generate_executive_summary(
        _inputs(
            critical_risk_count=0,
            overdue_actions=0,
            deteriorating_count=0,
            high_risk_count=2,
        )
    )
    assert "2 High risk suppliers" in s


def test_no_cta_when_clean_portfolio():
    s = generate_executive_summary(
        _inputs(
            critical_risk_count=0,
            overdue_actions=0,
            deteriorating_count=0,
            high_risk_count=0,
        )
    )
    assert "prioritise" not in s.lower()


# ── Period label ──────────────────────────────────────────────────────────────


def test_period_label_appears_in_esg_sentence():
    s = generate_executive_summary(
        _inputs(avg_esg_score=75.0, period_label="for Q1 2026")
    )
    assert "for Q1 2026" in s


# ── Output format ─────────────────────────────────────────────────────────────


def test_output_is_single_string():
    result = generate_executive_summary(_inputs())
    assert isinstance(result, str)
    assert len(result) > 50


def test_sentence_count_in_range():
    result = generate_executive_summary(
        _inputs(
            critical_risk_count=1,
            high_risk_count=2,
            overdue_actions=3,
            assessments_awaiting_review=2,
            top_risk_country="Italy",
            top_risk_sector="Energy",
        )
    )
    # Count sentences by period-space or period-end
    sentences = [s.strip() for s in result.replace(". ", ".|").replace(".", "").split("|") if s.strip()]
    # Should produce between 4 and 8 sentences
    sentence_count = result.count(". ") + (1 if result.endswith(".") else 0)
    assert 4 <= sentence_count <= 8
