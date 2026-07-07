"""Health Engine — Deterministic Supplier Digital Twin scoring.

Maps (signal_type, severity) → (health_dimension, health_delta).

All scoring is DETERMINISTIC and AUDITABLE. No LLM-based scoring.
Every output can be fully explained from this mapping table.

Health dimensions: 0–100, 100 = perfect health.
Negative deltas represent deterioration from adverse events.
Health recovers gradually over time if no new events occur.
"""

from __future__ import annotations

# ── Signal type → primary health dimension ────────────────────────────────────

SIGNAL_TO_DIMENSION: dict[str, str] = {
    # Country / geopolitical
    "COUNTRY_RISK": "geopolitical_health",
    "GEOPOLITICAL": "geopolitical_health",
    "SANCTIONS": "financial_health",
    # ESG / environmental
    "ENVIRONMENTAL_VIOLATION": "environmental_health",
    "ESG_CONTROVERSY": "esg_health",
    "EMISSIONS_BREACH": "environmental_health",
    # Social / human rights
    "LABOUR_RIGHTS": "human_rights_health",
    "HUMAN_RIGHTS_VIOLATION": "human_rights_health",
    "CHILD_LABOUR": "human_rights_health",
    # Governance / corruption
    "CORRUPTION": "esg_health",
    "FRAUD": "financial_health",
    "BRIBERY": "esg_health",
    # Financial
    "FINANCIAL_DISTRESS": "financial_health",
    "CREDIT_DOWNGRADE": "financial_health",
    "INSOLVENCY": "financial_health",
    # Cyber
    "CYBER_INCIDENT": "cyber_health",
    "DATA_BREACH": "cyber_health",
    # Regulatory / compliance
    "REGULATORY_BREACH": "compliance_health",
    "COMPLIANCE_FAILURE": "compliance_health",
    "REGULATORY_INVESTIGATION": "compliance_health",
    # Operational
    "SUPPLY_CHAIN_DISRUPTION": "operational_health",
    "PRODUCT_RECALL": "operational_health",
    "OPERATIONAL_INCIDENT": "operational_health",
    # Default
    "OTHER": "esg_health",
}

# ── Severity → health delta (per dimension) ───────────────────────────────────
# Negative = health worsens. Positive = health improves (for corrective events).

SEVERITY_DELTA: dict[str, float] = {
    "CRITICAL": -18.0,
    "HIGH": -10.0,
    "MEDIUM": -5.0,
    "LOW": -2.0,
    "INFO": -0.5,
    # Positive events (used by corrective action event types)
    "POSITIVE": +8.0,
}

# ── Event type → category mapping ────────────────────────────────────────────

EVENT_TYPE_TO_CATEGORY: dict[str, str] = {
    "EXTERNAL_SIGNAL": "ESG",  # overridden by signal type
    "ASSESSMENT_COMPLETED": "COMPLIANCE",
    "FINDING_CREATED": "COMPLIANCE",
    "CERTIFICATE_EXPIRED": "COMPLIANCE",
    "REGULATION_PUBLISHED": "COMPLIANCE",
    "CORRECTIVE_ACTION": "COMPLIANCE",
    "COUNTRY_RISK_CHANGE": "GEOPOLITICAL",
    "NGO_REPORT": "ESG",
    "FINANCIAL_DOWNGRADE": "FINANCIAL",
    "SANCTIONS_LISTING": "FINANCIAL",
    "CYBER_INCIDENT": "CYBER",
    "ENVIRONMENTAL_INCIDENT": "ENVIRONMENTAL",
    "HUMAN_RIGHTS_REPORT": "HUMAN_RIGHTS",
    "SUPPLY_CHAIN_DISRUPTION": "OPERATIONAL",
}

# Category from signal type (when event_type == EXTERNAL_SIGNAL)
SIGNAL_TYPE_TO_CATEGORY: dict[str, str] = {
    "COUNTRY_RISK": "GEOPOLITICAL",
    "GEOPOLITICAL": "GEOPOLITICAL",
    "SANCTIONS": "FINANCIAL",
    "ENVIRONMENTAL_VIOLATION": "ENVIRONMENTAL",
    "ESG_CONTROVERSY": "ESG",
    "EMISSIONS_BREACH": "ENVIRONMENTAL",
    "LABOUR_RIGHTS": "HUMAN_RIGHTS",
    "HUMAN_RIGHTS_VIOLATION": "HUMAN_RIGHTS",
    "CHILD_LABOUR": "HUMAN_RIGHTS",
    "CORRUPTION": "ESG",
    "FRAUD": "FINANCIAL",
    "BRIBERY": "ESG",
    "FINANCIAL_DISTRESS": "FINANCIAL",
    "CREDIT_DOWNGRADE": "FINANCIAL",
    "INSOLVENCY": "FINANCIAL",
    "CYBER_INCIDENT": "CYBER",
    "DATA_BREACH": "CYBER",
    "REGULATORY_BREACH": "COMPLIANCE",
    "COMPLIANCE_FAILURE": "COMPLIANCE",
    "REGULATORY_INVESTIGATION": "COMPLIANCE",
    "SUPPLY_CHAIN_DISRUPTION": "OPERATIONAL",
    "PRODUCT_RECALL": "OPERATIONAL",
    "OPERATIONAL_INCIDENT": "OPERATIONAL",
    "OTHER": "ESG",
}


def resolve_dimension(signal_type: str) -> str:
    """Return the health dimension most affected by this signal type."""
    return SIGNAL_TO_DIMENSION.get(signal_type.upper(), "esg_health")


def resolve_category(event_type: str, signal_type: str = "") -> str:
    """Return the event category for display."""
    if event_type == "EXTERNAL_SIGNAL" and signal_type:
        return SIGNAL_TYPE_TO_CATEGORY.get(signal_type.upper(), "ESG")
    return EVENT_TYPE_TO_CATEGORY.get(event_type, "ESG")


def compute_delta(severity: str, signal_type: str = "") -> float:
    """Compute the health score delta for a given severity.

    Returns a negative float (health worsens) or positive float (health improves).
    All outputs are deterministic given the same inputs.
    """
    return SEVERITY_DELTA.get(severity.upper(), -2.0)


def apply_delta(current: float, delta: float) -> float:
    """Apply a health delta and clamp to [0, 100]."""
    return max(0.0, min(100.0, current + delta))


def compute_overall_health(twin_fields: dict[str, float]) -> float:
    """Compute overall health as a weighted average of all 8 dimensions.

    Weights reflect relative importance in enterprise supplier risk management.
    All weights are documented here and never change without an explicit decision.
    """
    weights = {
        "esg_health": 0.15,
        "compliance_health": 0.20,
        "financial_health": 0.15,
        "geopolitical_health": 0.10,
        "cyber_health": 0.10,
        "human_rights_health": 0.15,
        "environmental_health": 0.10,
        "operational_health": 0.05,
    }
    total = sum(twin_fields.get(k, 75.0) * w for k, w in weights.items())
    return round(total, 2)


def compute_trend(prev_overall: float, new_overall: float) -> str:
    """Determine health trend direction."""
    diff = new_overall - prev_overall
    if diff > 2.0:
        return "IMPROVING"
    if diff < -2.0:
        return "DETERIORATING"
    return "STABLE"
