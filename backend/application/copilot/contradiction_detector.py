"""Contradiction Detection Engine — M33.2.

Scans retrieved data cross-retriever for logical inconsistencies before
the LLM generates an answer, so the model can be instructed to address them.
Pure function — no I/O, no DB access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.enums import ContradictionType

from .retrieval.base import RetrievalResult


@dataclass
class ContradictionRecord:
    contradiction_type: str
    description: str
    involved_objects: list[dict] = field(default_factory=list)
    severity: str = "warning"
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _supplier_data(results: list[RetrievalResult]) -> list[dict]:
    for r in results:
        if r.retriever == "supplier_retriever":
            return r.data
    return []


def _compliance_data(results: list[RetrievalResult]) -> list[dict]:
    for r in results:
        if r.retriever == "compliance_retriever":
            return r.data
    return []


def _disclosure_data(results: list[RetrievalResult]) -> list[dict]:
    for r in results:
        if r.retriever == "disclosure_retriever":
            return r.data
    return []


def _executive_data(results: list[RetrievalResult]) -> dict:
    for r in results:
        if r.retriever == "executive_retriever" and r.data:
            return r.data[0] if isinstance(r.data[0], dict) else {}
    return {}


def detect_contradictions(results: list[RetrievalResult]) -> list[ContradictionRecord]:
    """Return all data contradictions found across retrieval results."""
    found: list[ContradictionRecord] = []

    suppliers = _supplier_data(results)
    compliance = _compliance_data(results)
    disclosures = _disclosure_data(results)
    executive = _executive_data(results)

    # 1. Low-risk supplier band vs Critical compliance gaps in the same org
    low_risk_suppliers = [s for s in suppliers if s.get("risk_band") in ("Low", "Moderate")]
    critical_gaps = [g for g in compliance if g.get("severity") == "Critical"]
    if low_risk_suppliers and critical_gaps:
        found.append(ContradictionRecord(
            contradiction_type=ContradictionType.RISK_VS_COMPLIANCE,
            description=(
                f"{len(low_risk_suppliers)} supplier(s) show Low/Moderate risk band "
                f"but {len(critical_gaps)} Critical compliance gap(s) exist in the organisation. "
                "Supplier risk scoring may not reflect regulatory exposure."
            ),
            involved_objects=(
                [{"type": "Supplier", "id": s["supplier_id"]} for s in low_risk_suppliers[:3]]
                + [{"type": "ComplianceGap", "id": g["gap_id"]} for g in critical_gaps[:3]]
            ),
            severity="warning",
        ))

    # 2. Disclosure completeness mismatch: advanced status but very low coverage
    advanced_statuses = {"Approved", "Published", "In Review", "Submitted"}
    weak_advanced = [
        d for d in disclosures
        if d.get("disclosure_status") in advanced_statuses
        and (d.get("coverage_score") or 1.0) < 0.30
    ]
    if weak_advanced:
        found.append(ContradictionRecord(
            contradiction_type=ContradictionType.DISCLOSURE_COMPLETENESS,
            description=(
                f"{len(weak_advanced)} disclosure response(s) have an advanced status "
                "(Approved/Published/In Review) but coverage below 30%. "
                "Disclosure readiness may be overstated."
            ),
            involved_objects=[
                {"type": "Disclosure", "id": d["response_id"]} for d in weak_advanced[:3]
            ],
            severity="warning",
        ))

    # 3. Critical findings without open remediation actions
    exec_critical = executive.get("critical_findings", 0)
    exec_open_recs = executive.get("open_recommendations", 0)
    if isinstance(exec_critical, int) and exec_critical > 0 and exec_open_recs == 0:
        found.append(ContradictionRecord(
            contradiction_type=ContradictionType.FINDING_WITHOUT_ACTION,
            description=(
                f"{exec_critical} critical finding(s) are present but no open "
                "remediation recommendations exist. Critical issues may be unaddressed."
            ),
            involved_objects=[],
            severity="critical",
        ))

    # 4. High ESG score vs Critical findings for same supplier
    for sup in suppliers:
        esg = sup.get("esg_score")
        critical_findings = sup.get("critical_findings", [])
        if esg is not None and esg > 80 and len(critical_findings) > 0:
            found.append(ContradictionRecord(
                contradiction_type=ContradictionType.SUPPLIER_SCORE_VS_FINDINGS,
                description=(
                    f"Supplier {sup.get('supplier_name', sup.get('supplier_id'))} "
                    f"has ESG score {esg:.0f}/100 (high) but {len(critical_findings)} "
                    "critical finding(s). Score may not reflect operational reality."
                ),
                involved_objects=[{"type": "Supplier", "id": sup["supplier_id"]}],
                severity="warning",
            ))

    # 5. Executive summary mismatch: exec reports 0 critical but supplier data shows critical findings
    supplier_critical_count = sum(len(s.get("critical_findings", [])) for s in suppliers)
    if isinstance(exec_critical, int) and exec_critical == 0 and supplier_critical_count > 0:
        found.append(ContradictionRecord(
            contradiction_type=ContradictionType.EXECUTIVE_SUMMARY_MISMATCH,
            description=(
                "Executive summary reports 0 critical findings but the supplier intelligence "
                f"layer shows {supplier_critical_count} critical finding(s). "
                "Data may be out of sync across modules."
            ),
            involved_objects=[],
            severity="warning",
        ))

    return found


def format_contradictions_for_prompt(contradictions: list[ContradictionRecord]) -> str:
    """Return a system-prompt section listing contradictions for the LLM to address."""
    if not contradictions:
        return ""
    lines = ["POTENTIAL DATA CONTRADICTIONS DETECTED (address these in your answer if relevant):"]
    for i, c in enumerate(contradictions, 1):
        lines.append(f"  {i}. [{c.contradiction_type}] {c.description}")
    return "\n".join(lines)


def contradictions_to_dicts(contradictions: list[ContradictionRecord]) -> list[dict]:
    """Convert ContradictionRecords to JSON-serialisable dicts for persistence."""
    return [
        {
            "contradiction_type": c.contradiction_type,
            "description": c.description,
            "involved_objects": c.involved_objects,
            "severity": c.severity,
            "detected_at": c.detected_at,
        }
        for c in contradictions
    ]
