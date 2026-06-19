"""LkSG Annual Report Engine — M32.1.

Lieferkettensorgfaltspflichtengesetz (German Supply Chain Due Diligence Act).
All functions are pure: no I/O, no side effects.

Inputs are plain dicts assembled by the API layer from existing models.
Output is a structured snapshot dict ready for storage in DueDiligenceReport.report_data.
"""

from __future__ import annotations

_HR_CATEGORIES = frozenset(
    {
        "human rights", "labour", "labor", "workforce", "social",
        "child labour", "child labor", "forced labour", "forced labor",
        "discrimination", "health", "safety", "freedom of association",
        "living wage", "working conditions",
    }
)

_ENV_CATEGORIES = frozenset(
    {
        "environmental", "climate", "emissions", "pollution", "waste",
        "biodiversity", "water", "greenhouse", "deforestation",
    }
)

_FRAMEWORK = "LkSG"
_FRAMEWORK_VERSION = "2023"


def _is_hr(finding: dict) -> bool:
    cat = (finding.get("category") or "").lower()
    title = (finding.get("title") or "").lower()
    return any(kw in cat or kw in title for kw in _HR_CATEGORIES)


def _is_env(finding: dict) -> bool:
    cat = (finding.get("category") or "").lower()
    title = (finding.get("title") or "").lower()
    return any(kw in cat or kw in title for kw in _ENV_CATEGORIES)


def _risk_band_order(band: str) -> int:
    return {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1}.get(band, 0)


def build_lksgg_report(
    *,
    organization_id: str,
    reporting_year: int,
    suppliers: list[dict],
    supplier_scores: dict[str, dict],
    findings: list[dict],
    risks: list[dict],
    recommendations: list[dict],
    compliance_gaps: list[dict],
    controls: list[dict],
    evidence_items: list[dict],
) -> dict:
    """Build LkSG Annual Report snapshot.

    Args:
        suppliers: list of {id, name, tier, country, industry, status}
        supplier_scores: mapping supplier_id → {esg_score, risk_score, risk_band, trend}
        findings: list of {id, supplier_id, title, severity, category}
        risks: list of {id, supplier_id, title, severity, risk_level, category}
        recommendations: list of {id, supplier_id, title, action_status, due_date, priority}
        compliance_gaps: list of {id, supplier_id, severity, is_resolved, gap_type}
        controls: list of {id, title, control_type, effectiveness, status}
        evidence_items: list of {reliability_score, evidence_type}

    Returns:
        Serialisable snapshot dict for report_data.
    """
    # ── Supplier inventory ──────────────────────────────────────────────────
    tier_counts: dict[str, int] = {}
    for s in suppliers:
        tier = s.get("tier", "Other")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # ── Risk classification ─────────────────────────────────────────────────
    band_counts: dict[str, int] = {"Critical": 0, "High": 0, "Moderate": 0, "Low": 0}
    for s in suppliers:
        score = supplier_scores.get(s["id"])
        band = (score.get("risk_band") if score else None) or "Low"
        band_counts[band] = band_counts.get(band, 0) + 1

    # ── Critical supplier list (Critical or High band) ──────────────────────
    critical_suppliers = []
    for s in suppliers:
        score = supplier_scores.get(s["id"])
        band = (score.get("risk_band") if score else None) or "Low"
        if band in ("Critical", "High"):
            supplier_findings = [f for f in findings if f.get("supplier_id") == s["id"]]
            supplier_recs = [r for r in recommendations if r.get("supplier_id") == s["id"]]
            overdue = sum(1 for r in supplier_recs if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False))
            open_actions = sum(1 for r in supplier_recs if r.get("action_status") in ("open", "in_progress"))
            critical_suppliers.append({
                "supplier_id": s["id"],
                "supplier_name": s.get("name", ""),
                "country": s.get("country", ""),
                "tier": s.get("tier", ""),
                "risk_band": band,
                "esg_score": score.get("esg_score", 100.0) if score else 100.0,
                "risk_score": score.get("risk_score", 0.0) if score else 0.0,
                "trend": score.get("trend", "Stable") if score else "Stable",
                "critical_findings": sum(1 for f in supplier_findings if f.get("severity") == "Critical"),
                "high_findings": sum(1 for f in supplier_findings if f.get("severity") == "High"),
                "open_actions": open_actions,
                "overdue_actions": overdue,
            })
    critical_suppliers.sort(key=lambda x: -x["risk_score"])

    # ── Human rights findings ───────────────────────────────────────────────
    hr_findings = [f for f in findings if _is_hr(f)]
    hr_suppliers = {f.get("supplier_id") for f in hr_findings if f.get("supplier_id")}

    # ── Environmental findings ──────────────────────────────────────────────
    env_findings = [f for f in findings if _is_env(f)]
    env_suppliers = {f.get("supplier_id") for f in env_findings if f.get("supplier_id")}

    # ── Preventive measures ─────────────────────────────────────────────────
    preventive_controls = [c for c in controls if c.get("control_type") == "Preventive"]
    pm_count = len(preventive_controls)

    # ── Remediation ─────────────────────────────────────────────────────────
    open_recs = sum(1 for r in recommendations if r.get("action_status") == "open")
    in_progress_recs = sum(1 for r in recommendations if r.get("action_status") == "in_progress")
    resolved_recs = sum(1 for r in recommendations if r.get("action_status") in ("resolved", "verified"))
    overdue_recs = sum(1 for r in recommendations if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False))
    total_recs = len(recommendations)
    closure_rate = round(resolved_recs / total_recs, 4) if total_recs else 0.0

    # ── Evidence coverage (simple ratio of items with high reliability) ─────
    if evidence_items:
        avg_reliability = sum(
            (e.get("reliability_score") or 0.5) for e in evidence_items
        ) / len(evidence_items)
        evidence_coverage = round(min(1.0, avg_reliability), 4)
    else:
        evidence_coverage = 0.0

    # ── Unresolved high-risk suppliers ─────────────────────────────────────
    unresolved_gaps_by_supplier: dict[str, int] = {}
    for gap in compliance_gaps:
        if not gap.get("is_resolved"):
            sid = gap.get("supplier_id")
            if sid:
                unresolved_gaps_by_supplier[sid] = unresolved_gaps_by_supplier.get(sid, 0) + 1

    unresolved_suppliers = []
    for s in suppliers:
        gap_count = unresolved_gaps_by_supplier.get(s["id"], 0)
        score = supplier_scores.get(s["id"])
        band = (score.get("risk_band") if score else None) or "Low"
        if gap_count > 0 and band in ("Critical", "High"):
            unresolved_suppliers.append({
                "supplier_id": s["id"],
                "supplier_name": s.get("name", ""),
                "risk_band": band,
                "unresolved_gaps": gap_count,
            })
    unresolved_suppliers.sort(key=lambda x: -x["unresolved_gaps"])

    # ── Explainability ──────────────────────────────────────────────────────
    total_findings = len(findings)
    total_critical = sum(1 for f in findings if f.get("severity") == "Critical")
    total_high = sum(1 for f in findings if f.get("severity") == "High")

    explainability = [
        {
            "factor": "supplier_inventory",
            "value": len(suppliers),
            "description": f"{len(suppliers)} suppliers assessed across {len(tier_counts)} tiers",
        },
        {
            "factor": "critical_risk_suppliers",
            "value": band_counts.get("Critical", 0),
            "description": f"{band_counts.get('Critical', 0)} suppliers in Critical risk band",
        },
        {
            "factor": "human_rights_exposure",
            "value": len(hr_findings),
            "description": f"{len(hr_findings)} human rights findings across {len(hr_suppliers)} suppliers",
        },
        {
            "factor": "environmental_exposure",
            "value": len(env_findings),
            "description": f"{len(env_findings)} environmental findings across {len(env_suppliers)} suppliers",
        },
        {
            "factor": "remediation_closure",
            "value": closure_rate,
            "description": f"{resolved_recs}/{total_recs} actions resolved ({closure_rate:.1%})",
        },
        {
            "factor": "evidence_coverage",
            "value": evidence_coverage,
            "description": f"Evidence coverage: {evidence_coverage:.1%} based on {len(evidence_items)} items",
        },
    ]

    return {
        "meta": {
            "framework": _FRAMEWORK,
            "framework_version": _FRAMEWORK_VERSION,
            "organization_id": organization_id,
            "reporting_year": reporting_year,
        },
        "supplier_inventory": {
            "total": len(suppliers),
            "by_tier": tier_counts,
            "active": sum(1 for s in suppliers if s.get("status", "Active") == "Active"),
        },
        "risk_classification": band_counts,
        "critical_suppliers": critical_suppliers[:20],
        "human_rights": {
            "total_findings": len(hr_findings),
            "critical_findings": sum(1 for f in hr_findings if f.get("severity") == "Critical"),
            "high_findings": sum(1 for f in hr_findings if f.get("severity") == "High"),
            "suppliers_impacted": len(hr_suppliers),
        },
        "environmental": {
            "total_findings": len(env_findings),
            "critical_findings": sum(1 for f in env_findings if f.get("severity") == "Critical"),
            "high_findings": sum(1 for f in env_findings if f.get("severity") == "High"),
            "suppliers_impacted": len(env_suppliers),
        },
        "preventive_measures": {
            "total": pm_count,
            "preventive_controls": pm_count,
        },
        "remediation": {
            "open": open_recs,
            "in_progress": in_progress_recs,
            "resolved": resolved_recs,
            "overdue": overdue_recs,
            "total": total_recs,
            "closure_rate": closure_rate,
        },
        "evidence_coverage": evidence_coverage,
        "open_actions": open_recs + in_progress_recs,
        "overdue_actions": overdue_recs,
        "unresolved_high_risk_suppliers": unresolved_suppliers[:10],
        "totals": {
            "total_findings": total_findings,
            "critical_findings": total_critical,
            "high_findings": total_high,
            "total_risks": len(risks),
            "total_compliance_gaps": len(compliance_gaps),
            "unresolved_gaps": sum(1 for g in compliance_gaps if not g.get("is_resolved")),
        },
        "explainability": explainability,
    }
