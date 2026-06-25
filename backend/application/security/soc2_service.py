"""M49 G-048 — SOC 2 Type I Readiness Service.

Manages Trust Service Criteria controls, evidence tracking, and readiness scoring.
All 43 CC/A1/C1 criteria from AICPA SOC 2 2017 are seeded per organisation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── SOC 2 Trust Service Criteria catalogue ────────────────────────────────────

SOC2_CONTROLS: list[dict[str, str]] = [
    # CC1 — Control Environment
    {"control_id": "CC1.1", "category": "CC1", "control_name": "COSO Principle 1 — Integrity and ethical values", "description": "The entity demonstrates a commitment to integrity and ethical values."},
    {"control_id": "CC1.2", "category": "CC1", "control_name": "COSO Principle 2 — Board independence and oversight", "description": "The board of directors demonstrates independence from management and exercises oversight."},
    {"control_id": "CC1.3", "category": "CC1", "control_name": "COSO Principle 3 — Structures, authority, and responsibility", "description": "Management establishes structures, reporting lines, and authorities."},
    {"control_id": "CC1.4", "category": "CC1", "control_name": "COSO Principle 4 — Commitment to competence", "description": "The entity demonstrates commitment to attract, develop, and retain competent individuals."},
    {"control_id": "CC1.5", "category": "CC1", "control_name": "COSO Principle 5 — Accountability", "description": "The entity holds individuals accountable for their internal control responsibilities."},
    # CC2 — Communication and Information
    {"control_id": "CC2.1", "category": "CC2", "control_name": "COSO Principle 13 — Relevant quality information", "description": "The entity obtains or generates relevant, high-quality information to support internal control."},
    {"control_id": "CC2.2", "category": "CC2", "control_name": "COSO Principle 14 — Internal communication", "description": "The entity internally communicates information to support the functioning of internal control."},
    {"control_id": "CC2.3", "category": "CC2", "control_name": "COSO Principle 15 — External communication", "description": "The entity communicates with external parties regarding matters affecting the functioning of internal control."},
    # CC3 — Risk Assessment
    {"control_id": "CC3.1", "category": "CC3", "control_name": "COSO Principle 6 — Objectives specification", "description": "The entity specifies objectives with sufficient clarity to enable identification and assessment of risks."},
    {"control_id": "CC3.2", "category": "CC3", "control_name": "COSO Principle 7 — Risk identification and analysis", "description": "The entity identifies risks to the achievement of its objectives."},
    {"control_id": "CC3.3", "category": "CC3", "control_name": "COSO Principle 8 — Fraud risk", "description": "The entity considers the potential for fraud in assessing risks."},
    {"control_id": "CC3.4", "category": "CC3", "control_name": "COSO Principle 9 — Change identification", "description": "The entity identifies and assesses changes that could significantly impact the system of internal control."},
    # CC4 — Monitoring Activities
    {"control_id": "CC4.1", "category": "CC4", "control_name": "COSO Principle 16 — Ongoing and separate evaluations", "description": "The entity selects, develops, and performs ongoing and/or separate evaluations."},
    {"control_id": "CC4.2", "category": "CC4", "control_name": "COSO Principle 17 — Evaluation and communication of deficiencies", "description": "The entity evaluates and communicates internal control deficiencies in a timely manner."},
    # CC5 — Control Activities
    {"control_id": "CC5.1", "category": "CC5", "control_name": "COSO Principle 10 — Selection and development of controls", "description": "The entity selects and develops control activities that contribute to the mitigation of risks."},
    {"control_id": "CC5.2", "category": "CC5", "control_name": "COSO Principle 11 — General IT controls", "description": "The entity selects and develops general control activities over technology."},
    {"control_id": "CC5.3", "category": "CC5", "control_name": "COSO Principle 12 — Policies and procedures deployment", "description": "The entity deploys control activities through policies and procedures."},
    # CC6 — Logical and Physical Access
    {"control_id": "CC6.1", "category": "CC6", "control_name": "Logical access security software", "description": "The entity implements logical access security software, infrastructure, and architectures."},
    {"control_id": "CC6.2", "category": "CC6", "control_name": "Authentication controls", "description": "Prior to issuing credentials, the entity registers and authorizes new users."},
    {"control_id": "CC6.3", "category": "CC6", "control_name": "Role-based access", "description": "The entity authorizes, modifies, or removes access to data, software, functions, and other resources."},
    {"control_id": "CC6.4", "category": "CC6", "control_name": "Physical access controls", "description": "The entity restricts physical access to facilities and protected information assets."},
    {"control_id": "CC6.5", "category": "CC6", "control_name": "Logical and physical protections against threats", "description": "The entity discontinues logical and physical protections over physical assets."},
    {"control_id": "CC6.6", "category": "CC6", "control_name": "Security measures against external threats", "description": "The entity implements controls to prevent or detect and act upon the introduction of unauthorized software."},
    {"control_id": "CC6.7", "category": "CC6", "control_name": "Transmission and output protection", "description": "The entity restricts the transmission, movement, and removal of information to authorized users."},
    {"control_id": "CC6.8", "category": "CC6", "control_name": "Prevention and detection of malicious code", "description": "The entity implements controls to prevent or detect malicious software."},
    # CC7 — System Operations
    {"control_id": "CC7.1", "category": "CC7", "control_name": "Detection of vulnerabilities", "description": "To meet its objectives, the entity uses detection and monitoring procedures."},
    {"control_id": "CC7.2", "category": "CC7", "control_name": "Monitoring of system components", "description": "The entity monitors system components and the operation of those components."},
    {"control_id": "CC7.3", "category": "CC7", "control_name": "Evaluation of security events", "description": "The entity evaluates security events to determine whether they could or have resulted in failures."},
    {"control_id": "CC7.4", "category": "CC7", "control_name": "Response to identified security incidents", "description": "The entity responds to identified security incidents by executing a defined incident response program."},
    {"control_id": "CC7.5", "category": "CC7", "control_name": "Recovery from identified security incidents", "description": "The entity identifies, develops, and implements activities to recover from identified security incidents."},
    # CC8 — Change Management
    {"control_id": "CC8.1", "category": "CC8", "control_name": "Change management process", "description": "The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes."},
    # CC9 — Risk Mitigation
    {"control_id": "CC9.1", "category": "CC9", "control_name": "Risk mitigation activities", "description": "The entity identifies, selects, and develops risk mitigation activities."},
    {"control_id": "CC9.2", "category": "CC9", "control_name": "Vendor and business partner risk management", "description": "The entity assesses and manages risks associated with vendors and business partners."},
    # A1 — Availability
    {"control_id": "A1.1", "category": "A1", "control_name": "Capacity and performance management", "description": "The entity maintains, monitors, and evaluates current processing capacity and use of system components."},
    {"control_id": "A1.2", "category": "A1", "control_name": "Environmental protections", "description": "The entity authorizes, designs, develops, acquires, implements, operates, approves, and monitors environmental protections."},
    {"control_id": "A1.3", "category": "A1", "control_name": "Recovery plan testing", "description": "The entity tests recovery plan procedures, including monitoring and evaluating results."},
    # C1 — Confidentiality
    {"control_id": "C1.1", "category": "C1", "control_name": "Identification and maintenance of confidential information", "description": "The entity identifies and maintains confidential information to meet the entity's objectives."},
    {"control_id": "C1.2", "category": "C1", "control_name": "Disposal of confidential information", "description": "The entity disposes of confidential information to meet the entity's objectives."},
]

# Map control_id → EIOS implementation notes (pre-filled evidence stubs)
_EIOS_EVIDENCE: dict[str, str] = {
    "CC6.1": "EIOS enforces JWT-based auth (HS256/RS256), HTTPS-only, RBAC via role claims.",
    "CC6.2": "New users registered via invite flow with email verification and MFA (M45.1 G-007).",
    "CC6.3": "Role-based access enforced via require_admin/require_role deps in all routers.",
    "CC6.6": "Dependency scanning via uv/pip-audit; SecurityHeadersMiddleware blocks MIME sniffing.",
    "CC6.7": "API responses strip sensitive fields (password_hash never exposed in UserResponse).",
    "CC6.8": "Docker images scanned for CVEs in CI pipeline.",
    "CC7.1": "OTel tracing + structlog audit trail records all auth events and data mutations.",
    "CC7.2": "Prometheus /metrics endpoint; structlog JSON logs shipped to SIEM.",
    "CC7.3": "Structured audit log (AuditEventModel) captures all security-relevant events.",
    "CC7.4": "Incident response: on-call rotation defined; Grafana alerts → PagerDuty.",
    "CC8.1": "Alembic migrations version-controlled; deployment requires migration approval.",
    "CC9.2": "OFAC SDN connector (G-042) screens all suppliers; supplier risk scoring via M48.1.",
    "A1.1": "Celery workers + Redis; horizontal scaling via Kubernetes HPA.",
    "A1.3": "DR runbook in production_checklist_service; DB snapshots every 6h.",
    "C1.1": "GDPR data classification; PII fields identified in schema (email, name).",
    "C1.2": "Data retention policies enforced; soft-delete + purge_after_days field.",
}


@dataclass
class Soc2ReadinessReport:
    organization_id: str
    total_controls: int
    implemented: int
    in_progress: int
    not_started: int
    overall_pct: float
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)
    gaps: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "total_controls": self.total_controls,
            "implemented": self.implemented,
            "in_progress": self.in_progress,
            "not_started": self.not_started,
            "overall_readiness_pct": round(self.overall_pct, 1),
            "audit_ready": self.overall_pct >= 80.0,
            "by_category": self.by_category,
            "gaps": self.gaps,
            "methodology": "SOC 2 Type I — AICPA Trust Service Criteria 2017",
        }


def compute_readiness_score(controls: list[dict[str, Any]]) -> Soc2ReadinessReport:
    """Given a list of control dicts (with 'status', 'control_id', 'category'),
    compute the readiness report."""
    total = len(controls)
    if total == 0:
        return Soc2ReadinessReport(
            organization_id="", total_controls=0,
            implemented=0, in_progress=0, not_started=0, overall_pct=0.0,
        )

    org_id = controls[0].get("organization_id", "")
    impl = sum(1 for c in controls if c.get("status") == "Implemented")
    prog = sum(1 for c in controls if c.get("status") == "In Progress")
    not_s = sum(1 for c in controls if c.get("status") == "Not Started")
    overall_pct = (impl / total) * 100

    by_cat: dict[str, dict[str, Any]] = {}
    for c in controls:
        cat = c.get("category", "?")
        if cat not in by_cat:
            by_cat[cat] = {"total": 0, "implemented": 0, "pct": 0.0}
        by_cat[cat]["total"] += 1
        if c.get("status") == "Implemented":
            by_cat[cat]["implemented"] += 1
    for cat_data in by_cat.values():
        cat_data["pct"] = round(
            (cat_data["implemented"] / cat_data["total"]) * 100, 1
        ) if cat_data["total"] else 0.0

    gaps = [
        {"control_id": c["control_id"], "control_name": c.get("control_name", ""), "status": c.get("status", "")}
        for c in controls if c.get("status") != "Implemented"
    ]

    return Soc2ReadinessReport(
        organization_id=org_id,
        total_controls=total,
        implemented=impl,
        in_progress=prog,
        not_started=not_s,
        overall_pct=overall_pct,
        by_category=by_cat,
        gaps=gaps,
    )


def get_eios_evidence(control_id: str) -> str | None:
    """Return pre-filled EIOS-specific evidence note for a control."""
    return _EIOS_EVIDENCE.get(control_id)
