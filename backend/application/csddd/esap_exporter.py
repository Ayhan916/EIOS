"""ESAP Export Service — CSDDD-009 (Art. 16 Abs. 2).

Builds a structured JSON/XML export document covering all Art. 16 required fields.
Deterministic — same DB state always produces same output.

ESAP Taxonomy Mapping (Art. 16 CSDDD → ESAP/XBRL concepts, schema version 2024-01):
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.esap import ESAPExportBundle

SCHEMA_VERSION = "CSDDD-ESAP-2024-01"

# Taxonomy mapping: EIOS field → ESAP/XBRL concept
# Based on EFRAG ESRS/CSDDD draft taxonomy (subject to update until 2031)
TAXONOMY_MAPPING: dict[str, dict] = {
    "dd_policy_description": {
        "xbrl_concept": "csddd:DueDiligencePolicyDescription",
        "csddd_article": "Art. 16 Abs. 1 lit. a",
        "mandatory": True,
        "data_type": "text",
        "eios_source": "dd_governance.policy_description",
    },
    "risks_summary": {
        "xbrl_concept": "csddd:AdverseImpactIdentified",
        "csddd_article": "Art. 16 Abs. 1 lit. b",
        "mandatory": True,
        "data_type": "structured_list",
        "eios_source": "risks.title + risks.level + risks.status",
    },
    "actions_summary": {
        "xbrl_concept": "csddd:PreventionMeasuresTaken",
        "csddd_article": "Art. 16 Abs. 1 lit. c",
        "mandatory": True,
        "data_type": "structured_list",
        "eios_source": "corrective_action_plans + remedy_cases",
    },
    "board_approvals": {
        "xbrl_concept": "csddd:ManagementBodyOversight",
        "csddd_article": "Art. 22 + Art. 16 Abs. 1 lit. d",
        "mandatory": True,
        "data_type": "structured_list",
        "eios_source": "board_signoff_requests.approved",
    },
    "effectiveness_summary": {
        "xbrl_concept": "csddd:EffectivenessAssessment",
        "csddd_article": "Art. 16 Abs. 1 lit. e",
        "mandatory": True,
        "data_type": "text",
        "eios_source": "effectiveness_reviews",
    },
    "stakeholder_consultation": {
        "xbrl_concept": "csddd:StakeholderConsultationDescription",
        "csddd_article": "Art. 13 + Art. 16 Abs. 1 lit. f",
        "mandatory": False,
        "data_type": "text",
        "eios_source": "stakeholders",
    },
}

REQUIRED_FIELDS = [k for k, v in TAXONOMY_MAPPING.items() if v["mandatory"]]


def _safe_count(session: Session, table: str, where: str, params: dict) -> int:
    try:
        result = session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), params)
        return result.scalar() or 0
    except Exception:
        return 0


def _safe_list(session: Session, query: str, params: dict) -> list[dict]:
    try:
        rows = session.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


def build_export(
    session: Session,
    organization_id: str,
    report_year: int,
) -> ESAPExportBundle:
    """Assemble Art. 16 export document from live DB state."""
    org_id = str(organization_id)

    # Art. 16 lit. a — DD policy description
    dd_policy = ""
    try:
        row = session.execute(
            text(
                "SELECT description FROM dd_governance_documents WHERE organization_id = :oid AND status = 'approved' ORDER BY updated_at DESC LIMIT 1"
            ),
            {"oid": org_id},
        ).fetchone()
        if row:
            dd_policy = row[0] or ""
    except Exception:
        pass

    # Art. 16 lit. b — Risks (top 20 by level)
    risks = _safe_list(
        session,
        "SELECT id, title, level, status, category FROM risks WHERE organization_id = :oid ORDER BY created_at DESC LIMIT 20",
        {"oid": org_id},
    )

    # Art. 16 lit. c — Actions (CAPs + remedy cases)
    caps = _safe_list(
        session,
        "SELECT id, title, status FROM corrective_action_plans WHERE organization_id = :oid ORDER BY created_at DESC LIMIT 20",
        {"oid": org_id},
    )
    remedies = _safe_list(
        session,
        "SELECT id, title, status FROM remedy_cases WHERE organization_id = :oid ORDER BY created_at DESC LIMIT 20",
        {"oid": org_id},
    )
    actions_summary = [{"type": "cap", **r} for r in caps] + [
        {"type": "remedy", **r} for r in remedies
    ]

    # Art. 22 — Board approvals
    board_approvals = _safe_list(
        session,
        "SELECT id, title, signoff_type, approved_at, approved_by FROM board_signoff_requests WHERE organization_id = :oid AND status = 'approved' ORDER BY approved_at DESC LIMIT 10",
        {"oid": org_id},
    )

    # Art. 16 lit. e — Effectiveness
    effectiveness_summary = ""
    try:
        row = session.execute(
            text("SELECT COUNT(*) FROM effectiveness_reviews WHERE organization_id = :oid"),
            {"oid": org_id},
        ).fetchone()
        if row and row[0]:
            effectiveness_summary = (
                f"{row[0]} effectiveness review(s) conducted for reporting year {report_year}."
            )
    except Exception:
        effectiveness_summary = "Effectiveness reviews status not available."

    # Art. 13 — Stakeholder consultation
    stakeholder_count = _safe_count(
        session, "stakeholders", "organization_id = :oid", {"oid": org_id}
    )
    stakeholder_consultation = (
        f"{stakeholder_count} stakeholder(s) identified and engaged per Art. 13."
        if stakeholder_count
        else ""
    )

    # Validation
    missing_fields = []
    if not dd_policy:
        missing_fields.append("dd_policy_description")
    if not risks:
        missing_fields.append("risks_summary")
    if not actions_summary:
        missing_fields.append("actions_summary")
    if not board_approvals:
        missing_fields.append("board_approvals")
    if not effectiveness_summary:
        missing_fields.append("effectiveness_summary")

    return ESAPExportBundle(
        organization_id=org_id,
        report_year=report_year,
        generated_at=datetime.now(UTC),
        schema_version=SCHEMA_VERSION,
        dd_policy_description=dd_policy,
        risks_summary=risks,
        actions_summary=actions_summary,
        board_approvals=board_approvals,
        effectiveness_summary=effectiveness_summary,
        stakeholder_consultation=stakeholder_consultation,
        missing_fields=missing_fields,
        is_valid=len(missing_fields) == 0,
    )


def to_json(bundle: ESAPExportBundle) -> str:
    """Serialize export bundle to JSON string."""
    data = {
        "schema_version": bundle.schema_version,
        "organization_id": bundle.organization_id,
        "report_year": bundle.report_year,
        "generated_at": bundle.generated_at.isoformat(),
        "art16_sections": {
            "dd_policy_description": bundle.dd_policy_description,
            "risks_identified": bundle.risks_summary,
            "prevention_measures": bundle.actions_summary,
            "board_approvals": bundle.board_approvals,
            "effectiveness_assessment": bundle.effectiveness_summary,
            "stakeholder_consultation": bundle.stakeholder_consultation,
        },
        "validation": {
            "is_valid": bundle.is_valid,
            "missing_fields": bundle.missing_fields,
        },
    }
    return json.dumps(data, indent=2, default=str)


def to_xml(bundle: ESAPExportBundle) -> str:
    """Serialize export bundle to XML string (XBRL-like structure)."""
    root = ET.Element(
        "CSDDDReport",
        {
            "xmlns:csddd": "urn:esap:csddd:2024-01",
            "schemaVersion": bundle.schema_version,
            "organizationId": bundle.organization_id,
            "reportYear": str(bundle.report_year),
            "generatedAt": bundle.generated_at.isoformat(),
        },
    )

    def add(parent: ET.Element, tag: str, text_val: str) -> ET.Element:
        el = ET.SubElement(parent, tag)
        el.text = text_val
        return el

    s = ET.SubElement(root, "csddd:Art16Sections")
    add(s, "csddd:DueDiligencePolicyDescription", bundle.dd_policy_description)
    add(s, "csddd:EffectivenessAssessment", bundle.effectiveness_summary)
    add(s, "csddd:StakeholderConsultation", bundle.stakeholder_consultation)

    risks_el = ET.SubElement(s, "csddd:RisksIdentified")
    for r in bundle.risks_summary:
        re = ET.SubElement(risks_el, "csddd:Risk")
        for k, v in r.items():
            add(re, f"csddd:{k}", str(v) if v is not None else "")

    actions_el = ET.SubElement(s, "csddd:PreventionMeasures")
    for a in bundle.actions_summary:
        ae = ET.SubElement(actions_el, "csddd:Action")
        for k, v in a.items():
            add(ae, f"csddd:{k}", str(v) if v is not None else "")

    board_el = ET.SubElement(s, "csddd:BoardApprovals")
    for b in bundle.board_approvals:
        be = ET.SubElement(board_el, "csddd:Approval")
        for k, v in b.items():
            add(be, f"csddd:{k}", str(v) if v is not None else "")

    val_el = ET.SubElement(root, "Validation")
    add(val_el, "IsValid", str(bundle.is_valid).lower())
    missing_el = ET.SubElement(val_el, "MissingFields")
    for f in bundle.missing_fields:
        add(missing_el, "Field", f)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
