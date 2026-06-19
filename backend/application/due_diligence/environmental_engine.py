"""Environmental Risk Report Engine — M32.1.

Aggregates findings and risks by environmental topic.
All functions are pure: no I/O, no side effects.
"""

from __future__ import annotations

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "emissions": ["emission", "carbon", "ghg", "co2", "greenhouse", "scope 1", "scope 2", "scope 3", "net zero"],
    "pollution": ["pollut", "contamin", "toxic", "chemical discharge", "effluent", "hazardous"],
    "waste": ["waste", "disposal", "recycling", "landfill", "e-waste", "hazardous waste"],
    "biodiversity": ["biodiversity", "habitat", "species", "deforestation", "land use", "ecosystem"],
    "water": ["water", "wastewater", "river", "groundwater", "discharge", "water stress", "water use"],
    "climate": ["climate", "flood", "drought", "extreme weather", "sea level", "temperature", "climate risk"],
}


def _classify_finding(finding: dict) -> list[str]:
    text = (
        (finding.get("title") or "") + " " + (finding.get("category") or "") + " " + (finding.get("description") or "")
    ).lower()
    matched = [topic for topic, kws in _TOPIC_KEYWORDS.items() if any(kw in text for kw in kws)]
    return matched or ["other"]


def build_environmental_report(
    *,
    organization_id: str,
    findings: list[dict],
    risks: list[dict],
    recommendations: list[dict],
    evidence_items: list[dict],
    controls: list[dict],
) -> dict:
    """Aggregate findings and risks by environmental topic.

    Args:
        findings: list of {id, supplier_id, title, severity, category, description}
        risks: list of {id, supplier_id, title, severity, risk_level, category}
        recommendations: list of {id, supplier_id, title, action_status, priority}
        evidence_items: list of {reliability_score, evidence_type}
        controls: list of {id, title, control_type, effectiveness, status}

    Returns:
        Serialisable snapshot dict.
    """
    # ── Classify findings by env topic ──────────────────────────────────────
    topic_findings: dict[str, list[dict]] = {t: [] for t in _TOPIC_KEYWORDS}
    topic_findings["other"] = []

    for finding in findings:
        for topic in _classify_finding(finding):
            topic_findings.setdefault(topic, []).append(finding)

    # ── Classify risks by env topic ─────────────────────────────────────────
    topic_risks: dict[str, list[dict]] = {t: [] for t in _TOPIC_KEYWORDS}

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
            "unresolved_risks": sum(1 for r in t_risks if r.get("risk_level") in ("Critical", "High")),
            "suppliers_impacted": len(suppliers),
        })

    topic_summaries.sort(key=lambda x: -(x["finding_count"] + x["risk_count"]))

    # ── Aggregate totals ────────────────────────────────────────────────────
    all_env_findings = [f for t in _TOPIC_KEYWORDS for f in topic_findings.get(t, [])]
    unique_env_finding_ids = {f.get("id") for f in all_env_findings if f.get("id")}

    all_suppliers = {f.get("supplier_id") for f in all_env_findings if f.get("supplier_id")}
    for risk in risks:
        text = ((risk.get("title") or "") + " " + (risk.get("category") or "")).lower()
        if any(kw in text for kw_list in _TOPIC_KEYWORDS.values() for kw in kw_list):
            if risk.get("supplier_id"):
                all_suppliers.add(risk["supplier_id"])

    # ── Mitigation controls ─────────────────────────────────────────────────
    env_controls = [c for c in controls if any(
        kw in (c.get("title") or "").lower()
        for kw in ["environmental", "emission", "climate", "waste", "water", "pollution", "carbon"]
    )]
    effective_controls = [c for c in env_controls if (c.get("effectiveness") or 0) >= 0.75]

    # ── Remediation ─────────────────────────────────────────────────────────
    open_recs = sum(1 for r in recommendations if r.get("action_status") == "open")
    resolved = sum(1 for r in recommendations if r.get("action_status") in ("resolved", "verified"))
    overdue = sum(1 for r in recommendations if r.get("action_status") in ("open", "in_progress") and r.get("overdue", False))

    # ── Unresolved risks across all topics ──────────────────────────────────
    all_env_risks = [r for t in _TOPIC_KEYWORDS for r in topic_risks.get(t, [])]
    unresolved_risks = [r for r in all_env_risks if r.get("risk_level") in ("Critical", "High")]

    # ── Evidence coverage ───────────────────────────────────────────────────
    evidence_count = len(evidence_items)
    avg_reliability = (
        sum((e.get("reliability_score") or 0.5) for e in evidence_items) / evidence_count
        if evidence_count else 0.0
    )

    return {
        "meta": {
            "framework": "ESRS E1-E5 / TCFD / GRI 300",
            "organization_id": organization_id,
        },
        "summary": {
            "total_env_findings": len(unique_env_finding_ids),
            "total_env_risks": len({r.get("id") for r in all_env_risks if r.get("id")}),
            "unresolved_risks": len(unresolved_risks),
            "suppliers_impacted": len(all_suppliers),
            "mitigation_controls": len(env_controls),
            "effective_controls": len(effective_controls),
            "open_remediation_actions": open_recs,
            "overdue_actions": overdue,
            "resolved_actions": resolved,
            "evidence_items": evidence_count,
            "avg_evidence_reliability": round(avg_reliability, 4),
        },
        "by_topic": topic_summaries,
        "mitigation": {
            "total_controls": len(env_controls),
            "effective": len(effective_controls),
            "partially_effective": sum(1 for c in env_controls if 0.4 <= (c.get("effectiveness") or 0) < 0.75),
            "ineffective": sum(1 for c in env_controls if 0 < (c.get("effectiveness") or 0) < 0.4),
            "unknown": sum(1 for c in env_controls if c.get("effectiveness") is None),
        },
        "remediation": {
            "open": open_recs,
            "resolved": resolved,
            "overdue": overdue,
            "total": len(recommendations),
        },
    }
