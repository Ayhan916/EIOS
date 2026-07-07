"""CSDDD Impact Severity Calculator — OECD RBC-aligned, fully deterministic.

No LLM. Reproducible for any combination of (gravity, scope, remediability, likelihood).
"""

from __future__ import annotations

from domain.enums import SeverityLevel


def compute_severity(gravity: int, scope: int, remediability: int) -> float:
    """Weighted OECD formula.

    Each dimension: 1 (lowest) – 5 (highest).
    Returns severity_score on a 0–10 scale.
    """
    _validate(gravity, "gravity")
    _validate(scope, "scope")
    _validate(remediability, "remediability")

    weighted = gravity * 0.40 + scope * 0.30 + remediability * 0.30
    score = (weighted - 1.0) / 4.0 * 10.0
    return round(max(0.0, min(10.0, score)), 2)


def compute_priority(severity_score: float, likelihood: int) -> float:
    """Priority = severity × (likelihood / 5).

    Likelihood: 1 (very unlikely) – 5 (certain/ongoing).
    """
    _validate(likelihood, "likelihood")
    return round(severity_score * (likelihood / 5.0), 2)


def classify(severity_score: float) -> str:
    if severity_score >= 8.0:
        return SeverityLevel.CRITICAL.value
    if severity_score >= 6.0:
        return SeverityLevel.HIGH.value
    if severity_score >= 3.0:
        return SeverityLevel.MEDIUM.value
    return SeverityLevel.LOW.value


def _validate(v: int, name: str) -> None:
    if not (1 <= v <= 5):
        raise ValueError(f"{name} must be between 1 and 5, got {v}")


# Convenience: compute all at once
def assess(gravity: int, scope: int, remediability: int, likelihood: int) -> dict:
    sev = compute_severity(gravity, scope, remediability)
    pri = compute_priority(sev, likelihood)
    return {
        "severity_score": sev,
        "priority_score": pri,
        "severity_level": classify(sev),
    }
