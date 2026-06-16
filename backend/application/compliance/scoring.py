"""
Assessment Quality Scoring

Computes a 0.0–1.0 quality score from extraction depth and compliance coverage.

Weights:
  40% — entity depth (findings + risks, capped at saturation thresholds)
  20% — recommendations (capped at 3+)
  40% — mandatory compliance framework coverage ratio

A verdict of "insufficient_evidence" caps the score at 0.3.
"""

from __future__ import annotations

from .coverage import ComplianceCoverageReport

_FINDING_SATURATION = 3
_RISK_SATURATION = 2
_REC_SATURATION = 3

_WEIGHT_ENTITY = 0.40
_WEIGHT_RECS = 0.20
_WEIGHT_COMPLIANCE = 0.40

_INSUFFICIENT_CAP = 0.30


def compute_quality_score(
    finding_count: int,
    risk_count: int,
    recommendation_count: int,
    coverage: ComplianceCoverageReport,
    verdict: str | None = None,
) -> float:
    entity_score = min(1.0, (finding_count + risk_count) / (_FINDING_SATURATION + _RISK_SATURATION))
    rec_score = min(1.0, recommendation_count / _REC_SATURATION)
    compliance_score = coverage.mandatory_coverage_ratio

    raw = (
        entity_score * _WEIGHT_ENTITY
        + rec_score * _WEIGHT_RECS
        + compliance_score * _WEIGHT_COMPLIANCE
    )

    if verdict == "insufficient_evidence":
        raw = min(raw, _INSUFFICIENT_CAP)

    return round(min(1.0, max(0.0, raw)), 4)
