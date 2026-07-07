"""CSDDD Due Diligence Report Engine — M32.1.

Corporate Sustainability Due Diligence Directive (EU 2024/1760).
All functions are pure: no I/O, no side effects.

Inputs are plain dicts assembled by the API layer.
Output is a structured snapshot dict for DueDiligenceReport.report_data.
"""

from __future__ import annotations

_FRAMEWORK = "CSDDD"
_FRAMEWORK_VERSION = "2024/1760"

_HIGH_RISK_COUNTRIES = frozenset(
    {
        "China",
        "India",
        "Bangladesh",
        "Myanmar",
        "Cambodia",
        "Pakistan",
        "Ethiopia",
        "Nigeria",
        "Democratic Republic of Congo",
        "Colombia",
        "Brazil",
        "Indonesia",
        "Malaysia",
        "Vietnam",
        "Philippines",
    }
)

_SEVERE_IMPACT_CATEGORIES = frozenset(
    {
        "human rights",
        "child labour",
        "forced labour",
        "slavery",
        "trafficking",
        "discrimination",
        "health",
        "safety",
        "environmental",
        "climate",
        "deforestation",
        "pollution",
        "emissions",
    }
)


def _is_severe(finding: dict) -> bool:
    cat = (finding.get("category") or "").lower()
    title = (finding.get("title") or "").lower()
    severity = (finding.get("severity") or "").lower()
    is_critical_or_high = severity in ("critical", "high")
    has_severe_cat = any(kw in cat or kw in title for kw in _SEVERE_IMPACT_CATEGORIES)
    return is_critical_or_high and has_severe_cat


def _is_hr_severe(finding: dict) -> bool:
    cat = (finding.get("category") or "").lower()
    hr_terms = {
        "human rights",
        "labour",
        "labor",
        "social",
        "child",
        "forced",
        "discrimination",
        "health",
        "safety",
    }
    return _is_severe(finding) and any(t in cat for t in hr_terms)


def _is_env_severe(finding: dict) -> bool:
    cat = (finding.get("category") or "").lower()
    env_terms = {
        "environmental",
        "climate",
        "emission",
        "pollution",
        "deforestation",
        "waste",
        "water",
    }
    return _is_severe(finding) and any(t in cat for t in env_terms)


def build_csddd_report(
    *,
    organization_id: str,
    suppliers: list[dict],
    supplier_scores: dict[str, dict],
    findings: list[dict],
    risks: list[dict],
    recommendations: list[dict],
    compliance_gaps: list[dict],
    evidence_items: list[dict],
) -> dict:
    """Build CSDDD Due Diligence Report snapshot.

    Args:
        suppliers: list of {id, name, tier, country, industry, status}
        supplier_scores: mapping supplier_id → {esg_score, risk_score, risk_band, trend}
        findings: list of {id, supplier_id, title, severity, category}
        risks: list of {id, supplier_id, title, severity, risk_level, category}
        recommendations: list of {id, supplier_id, title, action_status, due_date, priority}
        compliance_gaps: list of {id, supplier_id, severity, is_resolved, gap_type}
        evidence_items: list of {reliability_score, evidence_type}

    Returns:
        Serialisable snapshot dict for report_data.
    """
    # ── Supply chain mapping ────────────────────────────────────────────────
    tier_counts: dict[str, int] = {}
    for s in suppliers:
        tier = s.get("tier", "Other")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    high_risk_countries = [
        s.get("country", "") for s in suppliers if s.get("country", "") in _HIGH_RISK_COUNTRIES
    ]
    high_risk_country_counts: dict[str, int] = {}
    for c in high_risk_countries:
        high_risk_country_counts[c] = high_risk_country_counts.get(c, 0) + 1

    # ── Severe impacts ──────────────────────────────────────────────────────
    all_severe = [f for f in findings if _is_severe(f)]
    hr_severe = [f for f in all_severe if _is_hr_severe(f)]
    env_severe = [f for f in all_severe if _is_env_severe(f)]

    # ── Risk assessment ─────────────────────────────────────────────────────
    open_gaps = [g for g in compliance_gaps if not g.get("is_resolved")]
    resolved_gaps = [g for g in compliance_gaps if g.get("is_resolved")]
    critical_gaps = [g for g in open_gaps if g.get("severity") == "Critical"]

    open_risks = [r for r in risks if r.get("risk_level") in ("Critical", "High")]
    critical_risks = [r for r in risks if r.get("risk_level") == "Critical"]

    # ── Mitigated vs residual ───────────────────────────────────────────────
    identified_risks = len(open_gaps) + len(open_risks)
    mitigated_risks = len(resolved_gaps)
    residual_risks = len(open_gaps)

    # ── Supplier risk trends ────────────────────────────────────────────────
    improving = sum(
        1 for s in suppliers if (supplier_scores.get(s["id"]) or {}).get("trend") == "Improving"
    )
    stable = sum(
        1 for s in suppliers if (supplier_scores.get(s["id"]) or {}).get("trend") == "Stable"
    )
    deteriorating = sum(
        1 for s in suppliers if (supplier_scores.get(s["id"]) or {}).get("trend") == "Deteriorating"
    )
    no_score = len(suppliers) - improving - stable - deteriorating

    # ── Remediation progress ────────────────────────────────────────────────
    open_recs = sum(1 for r in recommendations if r.get("action_status") == "open")
    in_progress = sum(1 for r in recommendations if r.get("action_status") == "in_progress")
    resolved_recs = sum(
        1 for r in recommendations if r.get("action_status") in ("resolved", "verified")
    )
    overdue = sum(
        1
        for r in recommendations
        if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False)
    )
    total_recs = len(recommendations)
    closure_rate = round(resolved_recs / total_recs, 4) if total_recs else 0.0

    # ── Supplier readiness ──────────────────────────────────────────────────
    band_counts: dict[str, int] = {"Critical": 0, "High": 0, "Moderate": 0, "Low": 0}
    for s in suppliers:
        sc = supplier_scores.get(s["id"])
        band = (sc.get("risk_band") if sc else None) or "Low"
        band_counts[band] = band_counts.get(band, 0) + 1

    ready_count = band_counts.get("Low", 0) + band_counts.get("Moderate", 0)
    unready_count = band_counts.get("High", 0) + band_counts.get("Critical", 0)

    # ── Explainability ──────────────────────────────────────────────────────
    explainability = [
        {
            "conclusion": "severe_impact_identification",
            "source": "findings",
            "count": len(all_severe),
            "detail": f"{len(all_severe)} severe adverse impacts identified "
            f"({len(hr_severe)} human rights, {len(env_severe)} environmental)",
        },
        {
            "conclusion": "risk_residual",
            "source": "compliance_gaps",
            "count": residual_risks,
            "detail": f"{residual_risks} unresolved compliance gaps constitute residual risk",
        },
        {
            "conclusion": "supply_chain_coverage",
            "source": "suppliers",
            "count": len(suppliers),
            "detail": f"{len(suppliers)} suppliers mapped; {len(high_risk_countries)} "
            f"in high-risk jurisdictions",
        },
        {
            "conclusion": "supplier_readiness",
            "source": "supplier_scores",
            "count": ready_count,
            "detail": f"{ready_count} suppliers ready (Low/Moderate risk); "
            f"{unready_count} require urgent attention",
        },
        {
            "conclusion": "remediation_progress",
            "source": "recommendations",
            "count": resolved_recs,
            "detail": f"{resolved_recs}/{total_recs} actions resolved ({closure_rate:.1%}); "
            f"{overdue} overdue",
        },
    ]

    return {
        "meta": {
            "framework": _FRAMEWORK,
            "framework_version": _FRAMEWORK_VERSION,
            "organization_id": organization_id,
        },
        "supply_chain": {
            "total_suppliers": len(suppliers),
            "by_tier": tier_counts,
            "high_risk_countries": high_risk_country_counts,
            "high_risk_country_count": len(set(high_risk_countries)),
        },
        "severe_impacts": {
            "total": len(all_severe),
            "human_rights": len(hr_severe),
            "environmental": len(env_severe),
            "critical": sum(1 for f in all_severe if f.get("severity") == "Critical"),
        },
        "risk_assessment": {
            "identified_risks": identified_risks,
            "mitigated_risks": mitigated_risks,
            "residual_risks": residual_risks,
            "critical_risks": len(critical_risks),
            "critical_gaps": len(critical_gaps),
        },
        "supplier_risk_trends": {
            "improving": improving,
            "stable": stable,
            "deteriorating": deteriorating,
            "no_data": no_score,
        },
        "remediation_progress": {
            "open": open_recs,
            "in_progress": in_progress,
            "resolved": resolved_recs,
            "overdue": overdue,
            "total": total_recs,
            "closure_rate": closure_rate,
        },
        "governance_oversight": {
            "suppliers_with_critical_risk": band_counts.get("Critical", 0),
            "suppliers_with_high_risk": band_counts.get("High", 0),
            "executive_accountability": "Required for Critical-band suppliers",
        },
        "supplier_readiness": {
            "ready": ready_count,
            "not_ready": unready_count,
            "by_band": band_counts,
        },
        "critical_gaps": [
            {
                "gap_id": g.get("id", ""),
                "supplier_id": g.get("supplier_id", ""),
                "severity": g.get("severity", ""),
                "gap_type": g.get("gap_type", ""),
            }
            for g in critical_gaps[:20]
        ],
        "explainability": explainability,
    }
