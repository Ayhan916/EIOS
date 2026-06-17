"""
Canonical schema constants and normalization functions for EIOS extraction (M16).

Provides deterministic mapping from free-text LLM field values to canonical
domain enum values. These functions are the single source of truth used by:
  - The validator (validate parsed entities after regex extraction)
  - The parsers (normalize fields at parse time)

Normalization never raises: unknown values map to sensible defaults.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical enum values (string form used in ORM / domain)
# ---------------------------------------------------------------------------

SEVERITY_VALUES: frozenset[str] = frozenset({"Critical", "High", "Medium", "Low"})
CONFIDENCE_VALUES: frozenset[str] = frozenset({"High", "Medium", "Low"})
RISK_LEVEL_VALUES: frozenset[str] = frozenset({"Critical", "High", "Medium", "Low"})
PRIORITY_VALUES: frozenset[str] = frozenset({"Critical", "High", "Medium", "Low"})

# ---------------------------------------------------------------------------
# Normalization maps — handle common LLM output variations
# ---------------------------------------------------------------------------

_SEVERITY_MAP: dict[str, str] = {
    # Exact canonical values
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    # Common abbreviations and variants
    "crit": "Critical",
    "severe": "High",
    "moderate": "Medium",
    "minor": "Low",
    "very high": "Critical",
    "elevated": "High",
    "significant": "High",
    "minimal": "Low",
}

_CONFIDENCE_MAP: dict[str, str] = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    # Variants
    "strong": "High",
    "confident": "High",
    "certain": "High",
    "probable": "Medium",
    "moderate": "Medium",
    "uncertain": "Low",
    "weak": "Low",
    "limited": "Low",
}

# Severity and risk_level share the same canonical values
_RISK_LEVEL_MAP = _SEVERITY_MAP.copy()

_PRIORITY_MAP = _SEVERITY_MAP.copy()


# ---------------------------------------------------------------------------
# Normalization functions
# ---------------------------------------------------------------------------


def normalize_severity(raw: str) -> str:
    """Map arbitrary severity string to canonical value, defaulting to 'Medium'."""
    return _SEVERITY_MAP.get(raw.strip().lower(), "Medium")


def normalize_confidence(raw: str) -> str:
    """Map arbitrary confidence string to canonical value, defaulting to 'Medium'."""
    return _CONFIDENCE_MAP.get(raw.strip().lower(), "Medium")


def normalize_risk_level(raw: str) -> str:
    """Map arbitrary risk level string to canonical value, defaulting to 'Medium'."""
    return _RISK_LEVEL_MAP.get(raw.strip().lower(), "Medium")


def normalize_priority(raw: str) -> str:
    """Map arbitrary priority string to canonical value, defaulting to 'Medium'."""
    return _PRIORITY_MAP.get(raw.strip().lower(), "Medium")


def normalize_probability(raw: object) -> float | None:
    """Parse and clamp a probability value to [0.0, 1.0]."""
    if raw is None:
        return None
    try:
        v = float(str(raw).strip().rstrip("%"))
        if v > 1.0 and v <= 100.0:
            v = v / 100.0
        return max(0.0, min(1.0, v))
    except (ValueError, TypeError):
        return None


def normalize_impact(raw: object) -> float | None:
    """Parse and clamp an impact value to [0.0, 1.0]."""
    return normalize_probability(raw)  # same logic


def is_valid_severity(value: str) -> bool:
    return value in SEVERITY_VALUES


def is_valid_confidence(value: str) -> bool:
    return value in CONFIDENCE_VALUES


def is_valid_risk_level(value: str) -> bool:
    return value in RISK_LEVEL_VALUES


def strip_markdown(text: str) -> str:
    """Remove bold/italic/code markdown markers from a string."""
    import re

    text = re.sub(r"\*{1,3}", "", text)
    text = re.sub(r"_{1,2}", "", text)
    text = re.sub(r"`", "", text)
    return text.strip()
