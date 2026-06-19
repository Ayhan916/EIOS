"""Human Rights Report Engine — M32.1.

Aggregates findings, risks, and remediation actions by human rights topic.
All functions are pure: no I/O, no side effects.
"""

from __future__ import annotations

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "child_labour": ["child labour", "child labor", "child work", "underage", "minor worker"],
    "forced_labour": ["forced labour", "forced labor", "slavery", "trafficking", "bonded labour"],
    "discrimination": ["discriminat", "equalit", "harassment", "bias", "prejudice"],
    "health_safety": ["health", "safety", "accident", "injury", "hazard", "ppe", "protective equipment"],
    "freedom_of_association": ["union", "association", "collective bargain", "strike", "freedom of assembly"],
    "living_wage": ["wage", "salary", "compensation", "minimum wage", "living wage", "pay gap"],
    "working_conditions": ["overtime", "working hours", "rest period", "dormitory", "work conditions"],
}


def _classify_finding(finding: dict) -> list[str]:
    """Return all HR topics this finding belongs to."""
    text = (
        (finding.get("title") or "") + " " + (finding.get("category") or "") + " " + (finding.get("description") or "")
    ).lower()
    matched = [topic for topic, kws in _TOPIC_KEYWORDS.items() if any(kw in text for kw in kws)]
    return matched or ["other"]


def build_human_rights_report(
    *,
    organization_id: str,
    findings: list[dict],
    risks: list[dict],
    recommendations: list[dict],
    evidence_items: list[dict],
    controls: list[dict],
) -> dict:
    """Aggregate findings and risks by human rights topic.

    Args:
        findings: list of {id, supplier_id, title, severity, category, description}
        risks: list of {id, supplier_id, title, severity, risk_level, category}
        recommendations: list of {id, supplier_id, title, action_status, priority}
        evidence_items: list of {reliability_score, evidence_type}
        controls: list of {id, title, control_type, effectiveness, status}

    Returns:
        Serialisable snapshot dict.
    """
    # ── Classify findings by HR topic ───────────────────────────────────────
    topic_findings: dict[str, list[dict]] = {t: [] for t in _TOPIC_KEYWORDS}
    topic_findings["other"] = []

    for finding in findings:
        for topic in _classify_finding(finding):
            topic_findings.setdefault(topic, []).append(finding)

    # ── Classify risks by HR topic ──────────────────────────────────────────
    topic_risks: dict[str, list[dict]] = {t: [] for t in _TOPIC_KEYWORDS}
    topic_risks["other"] = []

    for risk in risks:
        text = ((risk.get("title") or "") + " " + (risk.get("category") or "")).lower()
        matched = [t for t, kws in _TOPIC_KEYWORDS.items() if any(kw in text for kw in kws)]
        for topic in matched or ["other"]:
            topic_risks.setdefault(topic, []).append(risk)

    # ── Build topic summaries ───────────────────────────────────────────────
    topic_summaries = []
    for topic, kws in _TOPIC_KEYWORDS.items():
        t_findings = topic_findings.get(topic, [])
        t_risks = topic_risks.get(topic, [])
        suppliers = {f.get("supplier_id") for f in t_findings if f.get("supplier_id")}
        suppliers |= {r.get("supplier_id") for r in t_risks if r.get("supplier_id")}

        topic_summaries.append({
            "topic": topic,
            "display_name": topic.replace("_", " ").title(),
            "finding_count": len(t_findings),
            "critical_findings": sum(1 for f in t_findings if f.get("severity") == "Critical"),
            "high_findings": sum(1 for f in t_findings if f.get("severity") == "High"),
            "risk_count": len(t_risks),
            "suppliers_impacted": len(suppliers),
            "keywords": kws,
        })

    # Sort by total findings descending
    topic_summaries.sort(key=lambda x: -(x["finding_count"] + x["risk_count"]))

    # ── Aggregate totals ────────────────────────────────────────────────────
    all_hr_findings = [f for t in _TOPIC_KEYWORDS for f in topic_findings.get(t, [])]
    unique_hr_finding_ids = {f.get("id") for f in all_hr_findings if f.get("id")}

    all_suppliers = {f.get("supplier_id") for f in all_hr_findings if f.get("supplier_id")}
    for risk in risks:
        text = ((risk.get("title") or "") + " " + (risk.get("category") or "")).lower()
        if any(kw in text for kw_list in _TOPIC_KEYWORDS.values() for kw in kw_list):
            if risk.get("supplier_id"):
                all_suppliers.add(risk["supplier_id"])

    # ── Remediation for HR findings ─────────────────────────────────────────
    open_recs = sum(1 for r in recommendations if r.get("action_status") == "open")
    in_progress = sum(1 for r in recommendations if r.get("action_status") == "in_progress")
    resolved = sum(1 for r in recommendations if r.get("action_status") in ("resolved", "verified"))
    overdue = sum(1 for r in recommendations if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False))

    # ── HR controls ─────────────────────────────────────────────────────────
    hr_controls = [c for c in controls if any(
        kw in (c.get("title") or "").lower()
        for kw in ["human rights", "labour", "social", "health", "safety", "discrimination"]
    )]

    # ── Evidence ────────────────────────────────────────────────────────────
    evidence_count = len(evidence_items)
    avg_reliability = (
        sum((e.get("reliability_score") or 0.5) for e in evidence_items) / evidence_count
        if evidence_count else 0.0
    )

    return {
        "meta": {
            "framework": "UN Guiding Principles on Business and Human Rights",
            "organization_id": organization_id,
        },
        "summary": {
            "total_hr_findings": len(unique_hr_finding_ids),
            "total_hr_risks": len({r.get("id") for t in _TOPIC_KEYWORDS for r in topic_risks.get(t, []) if r.get("id")}),
            "suppliers_impacted": len(all_suppliers),
            "open_remediation_actions": open_recs + in_progress,
            "overdue_actions": overdue,
            "resolved_actions": resolved,
            "hr_controls": len(hr_controls),
            "evidence_items": evidence_count,
            "avg_evidence_reliability": round(avg_reliability, 4),
        },
        "by_topic": topic_summaries,
        "remediation": {
            "open": open_recs,
            "in_progress": in_progress,
            "resolved": resolved,
            "overdue": overdue,
            "total": len(recommendations),
        },
    }
