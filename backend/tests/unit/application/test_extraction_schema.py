"""
Tests for application/extraction/schema.py — normalization functions (M16).

All tests are pure-Python with no I/O or domain imports so they run without
the full application stack.
"""

import pytest

from application.extraction.schema import (
    CONFIDENCE_VALUES,
    PRIORITY_VALUES,
    RISK_LEVEL_VALUES,
    SEVERITY_VALUES,
    is_valid_confidence,
    is_valid_risk_level,
    is_valid_severity,
    normalize_confidence,
    normalize_impact,
    normalize_priority,
    normalize_probability,
    normalize_risk_level,
    normalize_severity,
    strip_markdown,
)

# ---------------------------------------------------------------------------
# Canonical value sets
# ---------------------------------------------------------------------------


class TestCanonicalSets:
    def test_severity_has_four_values(self):
        assert {"Critical", "High", "Medium", "Low"} == SEVERITY_VALUES

    def test_confidence_has_three_values(self):
        assert {"High", "Medium", "Low"} == CONFIDENCE_VALUES

    def test_risk_level_has_four_values(self):
        assert {"Critical", "High", "Medium", "Low"} == RISK_LEVEL_VALUES

    def test_priority_has_four_values(self):
        assert {"Critical", "High", "Medium", "Low"} == PRIORITY_VALUES


# ---------------------------------------------------------------------------
# is_valid_* guards
# ---------------------------------------------------------------------------


class TestIsValidGuards:
    @pytest.mark.parametrize("val", ["Critical", "High", "Medium", "Low"])
    def test_valid_severity(self, val):
        assert is_valid_severity(val)

    def test_invalid_severity(self):
        assert not is_valid_severity("moderate")
        assert not is_valid_severity("CRITICAL")  # case-sensitive sentinel check
        assert not is_valid_severity("")

    @pytest.mark.parametrize("val", ["High", "Medium", "Low"])
    def test_valid_confidence(self, val):
        assert is_valid_confidence(val)

    def test_invalid_confidence(self):
        assert not is_valid_confidence("Critical")
        assert not is_valid_confidence("high")

    @pytest.mark.parametrize("val", ["Critical", "High", "Medium", "Low"])
    def test_valid_risk_level(self, val):
        assert is_valid_risk_level(val)

    def test_invalid_risk_level(self):
        assert not is_valid_risk_level("unknown")


# ---------------------------------------------------------------------------
# normalize_severity
# ---------------------------------------------------------------------------


class TestNormalizeSeverity:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Critical", "Critical"),
            ("critical", "Critical"),
            ("CRITICAL", "Critical"),
            ("High", "High"),
            ("high", "High"),
            ("Medium", "Medium"),
            ("medium", "Medium"),
            ("Low", "Low"),
            ("low", "Low"),
            # Variant forms
            ("crit", "Critical"),
            ("severe", "High"),
            ("very high", "Critical"),
            ("elevated", "High"),
            ("significant", "High"),
            ("moderate", "Medium"),
            ("minor", "Low"),
            ("minimal", "Low"),
        ],
    )
    def test_known_variants(self, raw, expected):
        assert normalize_severity(raw) == expected

    def test_unknown_defaults_to_medium(self):
        assert normalize_severity("unknown_value") == "Medium"
        assert normalize_severity("") == "Medium"
        assert normalize_severity("   ") == "Medium"

    def test_strips_whitespace(self):
        assert normalize_severity("  high  ") == "High"


# ---------------------------------------------------------------------------
# normalize_confidence
# ---------------------------------------------------------------------------


class TestNormalizeConfidence:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("High", "High"),
            ("high", "High"),
            ("Medium", "Medium"),
            ("medium", "Medium"),
            ("Low", "Low"),
            ("low", "Low"),
            # Variants
            ("strong", "High"),
            ("confident", "High"),
            ("certain", "High"),
            ("probable", "Medium"),
            ("moderate", "Medium"),
            ("uncertain", "Low"),
            ("weak", "Low"),
            ("limited", "Low"),
        ],
    )
    def test_known_variants(self, raw, expected):
        assert normalize_confidence(raw) == expected

    def test_unknown_defaults_to_medium(self):
        assert normalize_confidence("xyz") == "Medium"


# ---------------------------------------------------------------------------
# normalize_risk_level
# ---------------------------------------------------------------------------


class TestNormalizeRiskLevel:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("crit", "Critical"),
            ("severe", "High"),
            ("moderate", "Medium"),
            ("minimal", "Low"),
        ],
    )
    def test_known_variants(self, raw, expected):
        assert normalize_risk_level(raw) == expected

    def test_unknown_defaults_to_medium(self):
        assert normalize_risk_level("n/a") == "Medium"


# ---------------------------------------------------------------------------
# normalize_priority
# ---------------------------------------------------------------------------


class TestNormalizePriority:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("elevated", "High"),
            ("minor", "Low"),
        ],
    )
    def test_known_variants(self, raw, expected):
        assert normalize_priority(raw) == expected

    def test_unknown_defaults_to_medium(self):
        assert normalize_priority("urgent") == "Medium"


# ---------------------------------------------------------------------------
# normalize_probability / normalize_impact
# ---------------------------------------------------------------------------


class TestNormalizeProbability:
    def test_already_fraction(self):
        assert normalize_probability(0.75) == 0.75

    def test_percentage_string_converts(self):
        assert normalize_probability("75%") == 0.75
        assert normalize_probability("50") == 0.5

    def test_clamps_above_one_when_not_percent(self):
        # Values >1 and <=100 are treated as percentages
        assert normalize_probability(80) == 0.8

    def test_clamps_below_zero(self):
        assert normalize_probability(-0.5) == 0.0

    def test_exact_boundaries(self):
        assert normalize_probability(0.0) == 0.0
        assert normalize_probability(1.0) == 1.0

    def test_none_returns_none(self):
        assert normalize_probability(None) is None

    def test_invalid_string_returns_none(self):
        assert normalize_probability("high") is None
        assert normalize_probability("n/a") is None

    def test_float_string(self):
        assert normalize_probability("0.42") == 0.42


class TestNormalizeImpact:
    def test_same_logic_as_probability(self):
        assert normalize_impact(0.9) == 0.9
        assert normalize_impact("60%") == 0.6
        assert normalize_impact(None) is None
        assert normalize_impact("bad") is None


# ---------------------------------------------------------------------------
# strip_markdown
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    def test_removes_bold(self):
        assert strip_markdown("**bold text**") == "bold text"

    def test_removes_italic(self):
        assert strip_markdown("*italic*") == "italic"

    def test_removes_triple_asterisk(self):
        assert strip_markdown("***both***") == "both"

    def test_removes_underscore(self):
        assert strip_markdown("__underline__") == "underline"

    def test_removes_code_ticks(self):
        assert strip_markdown("`code`") == "code"

    def test_plain_text_unchanged(self):
        assert strip_markdown("plain text") == "plain text"

    def test_strips_outer_whitespace(self):
        assert strip_markdown("  hello  ") == "hello"
