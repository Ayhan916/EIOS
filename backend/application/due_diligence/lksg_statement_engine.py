"""LkSG §10 Annual Due Diligence Statement Engine.

Produces the structured "Erklärung zur Sorgfaltspflicht" required by
LkSG §10 (Berichterstattungspflicht). The output covers the 5 mandatory
reporting sections and must be published on the company website.

All functions are pure: no I/O, no side effects.

Reference: LkSG §10 Abs. 2 — required content:
  (a) Description of the due diligence measures (Sorgfaltspflichtenmaßnahmen)
  (b) Results of the risk analysis (Ergebnisse der Risikoanalyse)
  (c) Prioritisation decisions and justification (Priorisierungsentscheidungen)
  (d) Preventive and remediation measures (Präventions- und Abhilfemaßnahmen)
  (e) Effectiveness review (Ergebnis der Wirksamkeitsprüfung)
  (f) Complaint procedure / grievance mechanism (Beschwerdeverfahren — LkSG §8)
"""

from __future__ import annotations

_FRAMEWORK = "LkSG"
_FRAMEWORK_VERSION = "2023"
_LEGAL_BASIS = "Lieferkettensorgfaltspflichtengesetz (LkSG) vom 16. Juli 2021"

_HR_KEYWORDS = frozenset({
    "human rights", "labour", "labor", "child labour", "forced labour",
    "discrimination", "health", "safety", "freedom of association",
    "living wage", "trafficking", "modern slavery", "grievance",
})

_ENV_KEYWORDS = frozenset({
    "environmental", "climate", "emissions", "pollution", "waste",
    "biodiversity", "water", "mercury", "persistent organic",
    "hazardous", "deforestation",
})


def _categorise(finding: dict) -> str:
    text = ((finding.get("category") or "") + " " + (finding.get("title") or "")).lower()
    if any(k in text for k in _HR_KEYWORDS):
        return "human_rights"
    if any(k in text for k in _ENV_KEYWORDS):
        return "environmental"
    return "other"


def _effectiveness_label(rate: float) -> str:
    if rate >= 0.8:
        return "Effective"
    if rate >= 0.5:
        return "Partially Effective"
    return "Requires Improvement"


def build_lksg_statement(
    *,
    organization_id: str,
    organization_name: str,
    reporting_year: int,
    suppliers: list[dict],
    supplier_scores: dict[str, dict],
    findings: list[dict],
    risks: list[dict],
    recommendations: list[dict],
    compliance_gaps: list[dict],
    controls: list[dict],
    evidence_items: list[dict],
    grievances: list[dict],
) -> dict:
    """Build the LkSG §10 Annual Due Diligence Statement.

    Args:
        grievances: list of {id, category, grievance_status} from grievance_reports table

    Returns:
        Serialisable snapshot dict for DueDiligenceReport.report_data.
        The dict maps directly to §10 Abs. 2 subsections (a)–(f).
    """

    # ── §10 Abs. 2 (a) — Due diligence measures in place ────────────────────
    tier_counts: dict[str, int] = {}
    for s in suppliers:
        tier = s.get("tier", "Unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    all_control_types: dict[str, int] = {}
    for c in controls:
        ct = c.get("control_type", "Unknown")
        all_control_types[ct] = all_control_types.get(ct, 0) + 1

    preventive_controls = [c for c in controls if c.get("control_type") == "Preventive"]
    detective_controls = [c for c in controls if c.get("control_type") == "Detective"]
    corrective_controls = [c for c in controls if c.get("control_type") == "Corrective"]

    measures = {
        "risk_analysis_conducted": True,
        "supplier_assessments": len({f.get("assessment_id", "") for f in findings}),
        "suppliers_assessed": len({f.get("supplier_id", "") for f in findings}),
        "control_framework_in_place": len(controls) > 0,
        "total_controls": len(controls),
        "by_type": all_control_types,
        "preventive_count": len(preventive_controls),
        "detective_count": len(detective_controls),
        "corrective_count": len(corrective_controls),
        "complaint_mechanism_operational": True,  # GAP-16 implemented
        "supplier_training_required": len(suppliers) > 0,
        "code_of_conduct_distributed": len(suppliers) > 0,
    }

    # ── §10 Abs. 2 (b) — Risk analysis results ──────────────────────────────
    by_category: dict[str, int] = {"human_rights": 0, "environmental": 0, "other": 0}
    by_severity: dict[str, int] = {}
    for f in findings:
        cat = _categorise(f)
        by_category[cat] = by_category.get(cat, 0) + 1
        sev = f.get("severity", "Low")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    band_counts: dict[str, int] = {"Critical": 0, "High": 0, "Moderate": 0, "Low": 0}
    for s in suppliers:
        sc = supplier_scores.get(s["id"])
        band = (sc.get("risk_band") if sc else None) or "Low"
        band_counts[band] = band_counts.get(band, 0) + 1

    high_risk_suppliers = [
        {
            "supplier_id": s["id"],
            "supplier_name": s.get("name", ""),
            "country": s.get("country", ""),
            "tier": s.get("tier", ""),
            "risk_band": (supplier_scores.get(s["id"]) or {}).get("risk_band", "Low"),
        }
        for s in suppliers
        if (supplier_scores.get(s["id"]) or {}).get("risk_band") in ("Critical", "High")
    ]
    high_risk_suppliers.sort(key=lambda x: x["risk_band"] == "Critical", reverse=True)

    risk_analysis = {
        "total_suppliers_in_scope": len(suppliers),
        "by_tier": tier_counts,
        "risk_classification": band_counts,
        "high_risk_supplier_count": len(high_risk_suppliers),
        "high_risk_suppliers_sample": high_risk_suppliers[:10],
        "total_findings": len(findings),
        "findings_by_category": by_category,
        "findings_by_severity": by_severity,
        "total_risks": len(risks),
        "open_compliance_gaps": sum(1 for g in compliance_gaps if not g.get("is_resolved")),
        "evidence_items_reviewed": len(evidence_items),
    }

    # ── §10 Abs. 2 (c) — Prioritisation decisions ───────────────────────────
    critical_count = band_counts.get("Critical", 0)
    high_count = band_counts.get("High", 0)
    total = len(suppliers) or 1

    prioritisation = {
        "framework": "Risk-based prioritisation per LkSG §5",
        "criteria": [
            "Severity of potential human rights / environmental impact",
            "Probability of occurrence based on country and sector risk",
            "Reversibility of adverse impact",
            "Number of people affected",
            "Supplier tier and level of EIOS control",
        ],
        "priority_1_suppliers": critical_count,
        "priority_2_suppliers": high_count,
        "prioritisation_coverage": f"{(critical_count + high_count) / total:.1%} of supply chain flagged for priority action",
        "justification": (
            f"Resources were directed first to {critical_count} Critical-risk suppliers, "
            f"then to {high_count} High-risk suppliers. Tier-1 suppliers were assessed "
            f"before Tier-2 and Tier-3 where risk information was unavailable."
        ),
    }

    # ── §10 Abs. 2 (d) — Preventive and remediation measures ───────────────
    open_recs = sum(1 for r in recommendations if r.get("action_status") == "open")
    in_progress_recs = sum(1 for r in recommendations if r.get("action_status") == "in_progress")
    resolved_recs = sum(1 for r in recommendations if r.get("action_status") in ("resolved", "verified"))
    overdue_recs = sum(1 for r in recommendations if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False))
    total_recs = len(recommendations)
    closure_rate = round(resolved_recs / total_recs, 4) if total_recs else 0.0

    actions_measures = {
        "preventive": {
            "total_controls": len(preventive_controls),
            "types": [c.get("title", "") for c in preventive_controls[:5]],
            "description": (
                "Preventive measures include supplier code of conduct requirements, "
                "contractual human rights clauses, risk-based questionnaire assessments, "
                "and on-site audit scheduling for Critical-risk suppliers."
            ),
        },
        "remediation": {
            "total_recommendations": total_recs,
            "open": open_recs,
            "in_progress": in_progress_recs,
            "resolved": resolved_recs,
            "overdue": overdue_recs,
            "closure_rate": closure_rate,
            "description": (
                f"{resolved_recs} of {total_recs} corrective actions resolved in {reporting_year}. "
                f"{overdue_recs} actions are overdue and subject to escalation."
            ),
        },
    }

    # ── §10 Abs. 2 (e) — Effectiveness review ───────────────────────────────
    label = _effectiveness_label(closure_rate)

    # Control effectiveness distribution
    eff_counts: dict[str, int] = {}
    for c in controls:
        eff = c.get("effectiveness", "Unknown")
        eff_counts[eff] = eff_counts.get(eff, 0) + 1

    effective_controls = eff_counts.get("Effective", 0) + eff_counts.get("effective", 0)
    total_controls = len(controls) or 1
    control_effectiveness_rate = round(effective_controls / total_controls, 4)

    effectiveness = {
        "overall_label": label,
        "remediation_closure_rate": closure_rate,
        "control_effectiveness_rate": control_effectiveness_rate,
        "effective_controls": effective_controls,
        "total_controls": len(controls),
        "by_effectiveness": eff_counts,
        "review_method": (
            "Effectiveness was assessed by comparing open vs. resolved corrective actions, "
            "measuring control effectiveness ratings, and reviewing evidence quality scores."
        ),
        "improvement_areas": (
            f"{overdue_recs} overdue actions require escalation. "
            f"Effectiveness for {len(controls) - effective_controls} controls rated below Effective."
        ),
    }

    # ── §10 Abs. 2 (f) — Complaint procedure / grievance mechanism ──────────
    total_grievances = len(grievances)
    by_status: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for g in grievances:
        gs = g.get("grievance_status", "received")
        by_status[gs] = by_status.get(gs, 0) + 1
        gc = g.get("category", "other")
        by_cat[gc] = by_cat.get(gc, 0) + 1

    resolved_grievances = by_status.get("resolved", 0)
    grievance_mechanism = {
        "mechanism_in_place": True,
        "legal_basis": "LkSG §8; CSDDD Art. 14",
        "accessible_to": [
            "Employees of direct suppliers",
            "Workers at indirect suppliers",
            "Trade union representatives",
            "Local community members",
            "NGOs and civil society organisations",
        ],
        "total_reports_received": total_grievances,
        "by_status": by_status,
        "by_category": by_cat,
        "resolved": resolved_grievances,
        "resolution_rate": round(resolved_grievances / total_grievances, 4) if total_grievances else 0.0,
        "confidentiality": (
            "Reporter identity is never disclosed to the subject of the report. "
            "Anonymous submissions are accepted. A reference code is issued to every reporter."
        ),
        "retaliation_protection": "Contractual and procedural protection against retaliation is in place.",
    }

    # ── Meta ─────────────────────────────────────────────────────────────────
    return {
        "meta": {
            "framework": _FRAMEWORK,
            "framework_version": _FRAMEWORK_VERSION,
            "legal_basis": _LEGAL_BASIS,
            "organization_id": organization_id,
            "organization_name": organization_name,
            "reporting_year": reporting_year,
            "report_type": "lksg_statement",
            "sections": ["(a) measures", "(b) risk_analysis", "(c) prioritisation",
                         "(d) actions", "(e) effectiveness", "(f) grievance"],
        },
        "section_a_measures": measures,
        "section_b_risk_analysis": risk_analysis,
        "section_c_prioritisation": prioritisation,
        "section_d_actions": actions_measures,
        "section_e_effectiveness": effectiveness,
        "section_f_grievance": grievance_mechanism,
        # Summary for dashboard / table views
        "summary": {
            "total_suppliers": len(suppliers),
            "high_risk_suppliers": len(high_risk_suppliers),
            "total_findings": len(findings),
            "open_actions": open_recs + in_progress_recs,
            "overdue_actions": overdue_recs,
            "closure_rate": closure_rate,
            "total_grievances": total_grievances,
            "effectiveness_label": label,
        },
    }
