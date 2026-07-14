"""AuditPackage domain value object (E5-F2).

Immutable snapshot of all audit-relevant data for a supplier over a given period.
Designed for handover to external auditors — no mutable state, no post-hoc changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class MethodologySnapshot:
    """Exact versions of all non-deterministic components used in this period.

    Attributes:
        formula_version:         RiskScore formula version (e.g. "RiskScore-v1.0").
        extraction_model:        LLM used for metric extraction (Haiku model ID).
        main_model:              LLM used for Copilot answers (Sonnet model ID).
        active_prompt_names:     Names of prompts active at package generation time.
    """

    formula_version: str
    extraction_model: str
    main_model: str
    active_prompt_names: tuple[str, ...]


@dataclass(frozen=True)
class AuditPackage:
    """Complete audit evidence bundle for one supplier over a given period.

    Attributes:
        package_id:         Stable UUID for this package.
        supplier_id:        The audited supplier.
        period_from:        Start of the audit period (inclusive).
        period_to:          End of the audit period (inclusive).
        generated_at:       When this package was assembled.
        generator_version:  "AuditPackage-v1.0" — bump on schema changes.
        methodology:        Version snapshot of all non-deterministic components.
        assessment_ids:     All assessment IDs active in the period.
        findings_count:     Total findings across all assessments in the period.
        risks_count:        Total risks across all assessments in the period.
        evidence_count:     Total evidence links across all findings.
        audit_event_count:  Audit log entries in the period for this supplier.
        risk_score:         Composite score at package generation time (0–100).
        risk_band:          Band at generation time (Low/Moderate/High/Critical).
    """

    package_id: str
    supplier_id: str
    period_from: datetime
    period_to: datetime
    generated_at: datetime
    generator_version: str
    methodology: MethodologySnapshot
    assessment_ids: tuple[str, ...]
    findings_count: int
    risks_count: int
    evidence_count: int
    audit_event_count: int
    risk_score: float
    risk_band: str
