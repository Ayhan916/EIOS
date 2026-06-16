"""
Extraction validator and quality report for EIOS (M16).

Validates and normalizes ParsedFinding, ParsedRisk, and ParsedRecommendation
objects after regex extraction.  Returns both the (possibly mutated) entities
and a list of human-readable warnings so operators can see what was corrected.

ExtractionReport is stored on the Assessment as extraction_metadata for full
auditability without additional database tables.

Design contract:
- Never discard an entity: a partially invalid entity is better than silence.
- Always normalise: unknown enum values are mapped to safe defaults.
- Always warn: corrections are recorded as non-fatal warnings.
- Zero entities from non-empty agent output is flagged as a quality concern.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from application.extraction.parsers import ParsedFinding, ParsedRisk, ParsedRecommendation
from application.extraction.schema import (
    normalize_confidence,
    normalize_impact,
    normalize_priority,
    normalize_probability,
    normalize_risk_level,
    normalize_severity,
    is_valid_severity,
    is_valid_confidence,
    is_valid_risk_level,
)


@dataclass
class ExtractionReport:
    """Captures quality metrics and warnings from a single extraction run."""

    # Raw counts (before validation)
    findings_raw: int = 0
    risks_raw: int = 0
    recommendations_raw: int = 0

    # Valid counts (after normalization — always same as raw in current design
    # since we normalise rather than reject)
    findings_valid: int = 0
    risks_valid: int = 0
    recommendations_valid: int = 0

    # Field-level normalization events
    normalization_count: int = 0

    # Non-fatal warnings to surface to operators
    warnings: list[str] = field(default_factory=list)

    # Which agent steps produced output that was parsed
    source_agent_types: list[str] = field(default_factory=list)

    # True when agent output was non-empty but zero entities were extracted
    # (indicates likely prompt/format drift)
    extraction_yield_zero: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def total_entities(self) -> int:
        return self.findings_valid + self.risks_valid + self.recommendations_valid


# ---------------------------------------------------------------------------
# Finding validation
# ---------------------------------------------------------------------------

def validate_findings(
    parsed: list[ParsedFinding],
    source_agent_type: str = "esg_assessment",
) -> tuple[list[ParsedFinding], list[str]]:
    """Validate and normalise parsed findings. Returns (normalised_list, warnings)."""
    warnings: list[str] = []
    normalised: list[ParsedFinding] = []

    for i, pf in enumerate(parsed):
        label = f"Finding {i + 1} '{pf.title[:40]}'"

        # Title must be non-empty
        if not pf.title or not pf.title.strip():
            warnings.append(f"{label}: empty title — skipping")
            continue

        # Severity normalisation
        if not is_valid_severity(pf.severity):
            normalised_severity = normalize_severity(pf.severity)
            warnings.append(
                f"{label}: severity '{pf.severity}' normalised to '{normalised_severity}'"
            )
            pf.severity = normalised_severity

        # Confidence normalisation
        if not is_valid_confidence(pf.confidence):
            normalised_conf = normalize_confidence(pf.confidence)
            warnings.append(
                f"{label}: confidence '{pf.confidence}' normalised to '{normalised_conf}'"
            )
            pf.confidence = normalised_conf

        # Description fallback
        if not pf.description or not pf.description.strip():
            pf.description = pf.title
            warnings.append(f"{label}: description was empty — using title as fallback")

        normalised.append(pf)

    return normalised, warnings


# ---------------------------------------------------------------------------
# Risk validation
# ---------------------------------------------------------------------------

def validate_risks(
    parsed: list[ParsedRisk],
) -> tuple[list[ParsedRisk], list[str]]:
    """Validate and normalise parsed risks. Returns (normalised_list, warnings)."""
    warnings: list[str] = []
    normalised: list[ParsedRisk] = []

    for i, pr in enumerate(parsed):
        label = f"Risk {i + 1} '{pr.title[:40]}'"

        if not pr.title or not pr.title.strip():
            warnings.append(f"{label}: empty title — skipping")
            continue

        # Risk level normalisation
        if not is_valid_risk_level(pr.risk_level):
            normalised_level = normalize_risk_level(pr.risk_level)
            warnings.append(
                f"{label}: risk_level '{pr.risk_level}' normalised to '{normalised_level}'"
            )
            pr.risk_level = normalised_level

        # Clamp probability and impact to [0.0, 1.0]
        if pr.probability is not None:
            clamped = normalize_probability(pr.probability)
            if clamped != pr.probability:
                warnings.append(
                    f"{label}: probability {pr.probability} clamped to {clamped}"
                )
            pr.probability = clamped

        if pr.impact is not None:
            clamped = normalize_impact(pr.impact)
            if clamped != pr.impact:
                warnings.append(
                    f"{label}: impact {pr.impact} clamped to {clamped}"
                )
            pr.impact = clamped

        # Description fallback
        if not pr.description or not pr.description.strip():
            pr.description = pr.title
            warnings.append(f"{label}: description was empty — using title as fallback")

        normalised.append(pr)

    return normalised, warnings


# ---------------------------------------------------------------------------
# Recommendation validation
# ---------------------------------------------------------------------------

def validate_recommendations(
    parsed: list[ParsedRecommendation],
) -> tuple[list[ParsedRecommendation], list[str]]:
    """Validate and normalise parsed recommendations. Returns (normalised_list, warnings)."""
    warnings: list[str] = []
    normalised: list[ParsedRecommendation] = []

    for i, pr in enumerate(parsed):
        label = f"Recommendation {i + 1} '{pr.title[:40]}'"

        if not pr.title or not pr.title.strip():
            warnings.append(f"{label}: empty title — skipping")
            continue

        # Priority normalisation
        if not is_valid_risk_level(pr.priority):
            normalised_prio = normalize_priority(pr.priority)
            warnings.append(
                f"{label}: priority '{pr.priority}' normalised to '{normalised_prio}'"
            )
            pr.priority = normalised_prio

        # Description fallback
        if not pr.description or not pr.description.strip():
            pr.description = pr.title
            warnings.append(f"{label}: description was empty — using title as fallback")

        normalised.append(pr)

    return normalised, warnings


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_extraction_report(
    *,
    raw_findings: list[ParsedFinding],
    valid_findings: list[ParsedFinding],
    raw_risks: list[ParsedRisk],
    valid_risks: list[ParsedRisk],
    raw_recommendations: list[ParsedRecommendation],
    valid_recommendations: list[ParsedRecommendation],
    all_warnings: list[str],
    step_outputs: dict[str, str],
) -> ExtractionReport:
    """Assemble the ExtractionReport from validation results."""
    source_agent_types = [k for k, v in step_outputs.items() if v and v.strip()]

    normalization_count = sum(
        1 for w in all_warnings
        if "normalised to" in w or "clamped to" in w or "fallback" in w
    )

    # Detect yield-zero: agent produced output but we extracted nothing
    extraction_yield_zero = bool(source_agent_types) and (
        len(valid_findings) == 0
        and len(valid_risks) == 0
        and len(valid_recommendations) == 0
    )

    if extraction_yield_zero:
        all_warnings.append(
            "No entities extracted despite non-empty agent output. "
            "The LLM may have used an unexpected output format."
        )

    return ExtractionReport(
        findings_raw=len(raw_findings),
        risks_raw=len(raw_risks),
        recommendations_raw=len(raw_recommendations),
        findings_valid=len(valid_findings),
        risks_valid=len(valid_risks),
        recommendations_valid=len(valid_recommendations),
        normalization_count=normalization_count,
        warnings=all_warnings,
        source_agent_types=source_agent_types,
        extraction_yield_zero=extraction_yield_zero,
    )
