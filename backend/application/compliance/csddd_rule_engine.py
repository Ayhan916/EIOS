"""CSDDD Obligation Rule Engine (ADR-010).

Deterministic, stateless mapping of Finding attributes to CSDDD articles.
No LLM is involved — all decisions are made by keyword/category rules.

LLMs may later be used to EXPLAIN a match, but never to DECIDE one.

Matching logic:
  EXACT match  — finding.category contains a trigger_condition keyword → confidence HIGH
  PARTIAL match — finding.title or finding.description contains a trigger_condition keyword
                  (and category did NOT match) → confidence MEDIUM

Severity filtering:
  If an obligation has a severity_threshold, the finding's severity must be >=
  that threshold for the obligation to trigger. Ordering: Low < Medium < High < Critical.

Usage:
    engine = CsdddRuleEngine()
    matches = engine.evaluate(finding_dict)
"""

from __future__ import annotations

from domain.csddd_obligation import CsdddObligation, ObligationMatch

# ── severity ordering ─────────────────────────────────────────────────────────

_SEVERITY_ORDER: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def _severity_meets_threshold(finding_severity: str | None, threshold: str | None) -> bool:
    if threshold is None:
        return True
    if finding_severity is None:
        return False
    return _SEVERITY_ORDER.get(finding_severity.lower(), 0) >= _SEVERITY_ORDER.get(
        threshold.lower(), 0
    )


# ── built-in CSDDD obligations registry ──────────────────────────────────────
# Source: EU Directive 2024/1760 — Corporate Sustainability Due Diligence
# Maintained by Legal/Compliance, not by AI (ADR-010).
# Each obligation is keyed by a stable article_id.

CSDDD_OBLIGATIONS: tuple[CsdddObligation, ...] = (
    # ── Art. 5 — Due diligence policy ────────────────────────────────────────
    CsdddObligation(
        article_id="csddd-art-5",
        article_number="Art. 5",
        obligation_text="Integrate due diligence into corporate policy and risk management system",
        trigger_conditions=("due diligence policy", "policy integration", "risk management", "corporate policy"),
        evidence_requirements=("approved due diligence policy", "board endorsement", "policy publication"),
        severity_threshold=None,
    ),
    # ── Art. 6 — Supply chain mapping ─────────────────────────────────────────
    CsdddObligation(
        article_id="csddd-art-6",
        article_number="Art. 6",
        obligation_text="Map and identify own operations and value chain scope for due diligence",
        trigger_conditions=("supply chain mapping", "value chain", "tier mapping", "supplier mapping", "scope identification"),
        evidence_requirements=("supply chain map", "tier-1 supplier list", "value chain scope document"),
        severity_threshold=None,
    ),
    CsdddObligation(
        article_id="csddd-art-7",
        article_number="Art. 7",
        obligation_text="Identify actual and potential adverse human rights and environmental impacts",
        trigger_conditions=("adverse impact", "impact identification", "human rights", "environmental"),
        evidence_requirements=("impact assessment", "stakeholder consultation", "supply chain mapping"),
        severity_threshold=None,
    ),
    CsdddObligation(
        article_id="csddd-art-7-2",
        article_number="Art. 7(2)",
        obligation_text="Prioritise identified adverse impacts based on severity and likelihood",
        trigger_conditions=("prioritisation", "severity assessment", "likelihood assessment", "impact prioritisation"),
        evidence_requirements=("prioritisation methodology", "risk matrix", "severity scoring documentation"),
        severity_threshold=None,
    ),
    CsdddObligation(
        article_id="csddd-art-8",
        article_number="Art. 8",
        obligation_text="Integrate due diligence into policies and management systems",
        trigger_conditions=("policy", "management system", "due diligence", "governance"),
        evidence_requirements=("due diligence policy", "management system documentation"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-8-1a",
        article_number="Art. 8(1)(a)",
        obligation_text="Require suppliers to adopt a code of conduct covering human rights and environmental standards",
        trigger_conditions=(
            "forced labour", "zwangsarbeit", "human rights violation", "child labour",
            "slavery", "trafficking", "supplier code", "code of conduct",
        ),
        evidence_requirements=("supplier code of conduct", "signed supplier commitment", "contractual clause"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-8-1b",
        article_number="Art. 8(1)(b)",
        obligation_text="Provide financial and technical support to suppliers to prevent adverse environmental impacts",
        trigger_conditions=(
            "environmental pollution", "umweltverschmutzung", "environmental damage",
            "emissions", "waste", "hazardous substances", "pollution", "contamination",
        ),
        evidence_requirements=("financial support records", "technical assistance agreement", "environmental improvement plan"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-8-3",
        article_number="Art. 8(3)",
        obligation_text="Obtain contractual assurances from business partners with cascading obligations",
        trigger_conditions=("contractual assurance", "cascading obligation", "contractual clause", "supplier contract"),
        evidence_requirements=("signed contracts with due diligence clauses", "cascading commitment letters"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-8-4",
        article_number="Art. 8(4)",
        obligation_text="Verify business partner compliance through independent audits",
        trigger_conditions=("audit", "third-party audit", "verification", "compliance check", "on-site inspection"),
        evidence_requirements=("audit report", "third-party audit certificate", "inspection records"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-9",
        article_number="Art. 9",
        obligation_text="Bring actual adverse impacts to an end or minimise their extent without delay",
        trigger_conditions=(
            "actual impact", "ongoing violation", "cessation", "immediate harm",
            "active abuse", "confirmed violation", "substantiated",
        ),
        evidence_requirements=("cessation evidence", "immediate corrective measures", "impact timeline"),
        severity_threshold="High",
    ),
    CsdddObligation(
        article_id="csddd-art-10",
        article_number="Art. 10",
        obligation_text="Prevent and mitigate potential adverse impacts — take preventive action plan",
        trigger_conditions=(
            "human rights", "child labour", "forced labour", "trafficking", "slavery",
            "labor", "labour", "working conditions",
        ),
        evidence_requirements=("preventive action plan", "supplier code of conduct", "contractual assurance"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-10-2a",
        article_number="Art. 10(2)(a)",
        obligation_text="Develop and implement a prevention action plan with reasonable timelines",
        trigger_conditions=("prevention plan", "corrective action", "remediation plan", "timeline"),
        evidence_requirements=("action plan with timelines", "milestones", "responsible owner"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-10-2b",
        article_number="Art. 10(2)(b)",
        obligation_text="Provide capacity-building support to SMEs in the value chain",
        trigger_conditions=("sme", "small supplier", "capacity building", "support", "training"),
        evidence_requirements=("capacity building programme", "sme support evidence"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-10-1",
        article_number="Art. 10(1)",
        obligation_text="Neutralise or minimise actual adverse impacts through compensation or restoration",
        trigger_conditions=("neutralisation", "restoration", "environmental restoration", "habitat restoration", "land remediation"),
        evidence_requirements=("restoration plan", "compensation scheme", "third-party environmental assessment"),
        severity_threshold="High",
    ),
    CsdddObligation(
        article_id="csddd-art-10-3",
        article_number="Art. 10(3)",
        obligation_text="Provide financial compensation to affected persons as a last resort",
        trigger_conditions=("financial compensation", "reparation payment", "victim compensation", "affected community fund"),
        evidence_requirements=("compensation agreement", "payment records", "beneficiary acknowledgement"),
        severity_threshold="High",
    ),
    CsdddObligation(
        article_id="csddd-art-11",
        article_number="Art. 11",
        obligation_text="Bring actual adverse impacts to an end or minimise their extent",
        trigger_conditions=(
            "human rights violation", "child labour", "forced labour", "pollution",
            "deforestation", "environmental damage", "discrimination",
        ),
        evidence_requirements=("remediation evidence", "cessation plan", "impact reduction measures"),
        severity_threshold="High",
    ),
    CsdddObligation(
        article_id="csddd-art-11-1",
        article_number="Art. 11(1)",
        obligation_text="Establish a grievance mechanism accessible to affected persons and communities",
        trigger_conditions=("grievance mechanism", "complaint channel", "hotline", "whistleblower", "reporting channel"),
        evidence_requirements=("grievance mechanism documentation", "accessibility evidence", "case log"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-11-2",
        article_number="Art. 11(2)",
        obligation_text="Allow trade unions and workers' representatives to submit grievances on behalf of affected workers",
        trigger_conditions=("trade union", "workers representative", "collective grievance", "labour union", "union"),
        evidence_requirements=("union engagement records", "collective grievance log", "worker representation agreement"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-12",
        article_number="Art. 12",
        obligation_text="Provide remediation for adverse impacts caused or contributed to",
        trigger_conditions=("remediation", "remedy", "compensation", "reparation", "restitution"),
        evidence_requirements=("remediation agreement", "compensation records", "grievance outcome"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-13",
        article_number="Art. 13",
        obligation_text="Meaningful engagement with stakeholders throughout due diligence process",
        trigger_conditions=("stakeholder", "community", "indigenous", "affected persons", "consultation"),
        evidence_requirements=("stakeholder engagement records", "consultation minutes", "feedback log"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-13-1",
        article_number="Art. 13(1)",
        obligation_text="Communicate due diligence findings annually in a public report",
        trigger_conditions=("annual report", "disclosure", "public communication", "sustainability report", "transparency"),
        evidence_requirements=("published annual report", "public disclosure statement", "csrd report"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-13-2",
        article_number="Art. 13(2)",
        obligation_text="Make due diligence communication available in machine-readable format",
        trigger_conditions=("machine readable", "structured data", "xbrl", "digital reporting", "esg data format"),
        evidence_requirements=("machine-readable sustainability data", "structured esg disclosure", "xbrl tagging"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-14",
        article_number="Art. 14",
        obligation_text="Establish a complaints and grievance mechanism accessible to affected persons",
        trigger_conditions=("grievance", "complaint", "whistleblower", "reporting channel", "hotline"),
        evidence_requirements=("grievance mechanism documentation", "case log", "resolution records"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-14-climate",
        article_number="Art. 14(2)",
        obligation_text="Adopt and implement a climate change mitigation transition plan aligned with Paris Agreement",
        trigger_conditions=("climate transition plan", "paris agreement", "net zero", "carbon neutrality", "1.5 degree", "science based target"),
        evidence_requirements=("climate transition plan", "sbti commitment", "ghg reduction targets"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-15",
        article_number="Art. 15",
        obligation_text="Monitor effectiveness of due diligence policy and measures",
        trigger_conditions=("monitoring", "effectiveness", "audit", "review", "kpi", "indicator"),
        evidence_requirements=("monitoring report", "effectiveness assessment", "kpi tracking"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-15-2",
        article_number="Art. 15(2)",
        obligation_text="Engage independent third-party verification of due diligence monitoring results",
        trigger_conditions=("third-party verification", "independent audit", "external assurance", "third party assurance"),
        evidence_requirements=("third-party assurance report", "auditor independence declaration"),
        severity_threshold="Medium",
    ),
    CsdddObligation(
        article_id="csddd-art-16",
        article_number="Art. 16",
        obligation_text="Communicate due diligence findings — annual public reporting",
        trigger_conditions=("disclosure", "reporting", "transparency", "csrd", "annual report"),
        evidence_requirements=("sustainability report", "disclosure statement", "published report"),
        severity_threshold="Low",
    ),
    CsdddObligation(
        article_id="csddd-art-22",
        article_number="Art. 22",
        obligation_text="Director oversight and responsibility for due diligence strategy",
        trigger_conditions=("governance", "board", "director", "executive", "management responsibility"),
        evidence_requirements=("board minutes", "director statement", "governance documentation"),
        severity_threshold="High",
    ),
    CsdddObligation(
        article_id="csddd-art-22-1",
        article_number="Art. 22(1)",
        obligation_text="Directors must consider due diligence consequences when acting in the company's best interest",
        trigger_conditions=("director duty", "fiduciary duty", "board decision", "executive accountability", "duty of care"),
        evidence_requirements=("board resolution on due diligence", "director sustainability report", "executive charter"),
        severity_threshold="High",
    ),
)

# Fast lookup by article_id
_OBLIGATIONS_BY_ID: dict[str, CsdddObligation] = {o.article_id: o for o in CSDDD_OBLIGATIONS}


# ── rule engine ───────────────────────────────────────────────────────────────


class CsdddRuleEngine:
    """Deterministic mapper: Finding attributes → CSDDD article obligations (ADR-010).

    The engine is stateless and instantiated with a set of obligations.
    The built-in set can be extended or replaced for testing.

    Example:
        engine = CsdddRuleEngine()
        matches = engine.evaluate({
            "title": "Child labour detected in tier-2 supplier",
            "category": "human rights",
            "severity": "Critical",
        })
    """

    def __init__(
        self,
        obligations: tuple[CsdddObligation, ...] = CSDDD_OBLIGATIONS,
    ) -> None:
        self._obligations = obligations

    def evaluate(self, finding: dict) -> list[ObligationMatch]:
        """Return all obligations triggered by this finding, ordered by article_id.

        Args:
            finding: Dict with keys: title (str), category (str), severity (str),
                     description (str, optional). All keys are optional — missing
                     values are treated as empty strings.

        Returns:
            List of ObligationMatch, sorted by article_id. Empty if no match.
        """
        category = (finding.get("category") or "").lower()
        title = (finding.get("title") or "").lower()
        description = (finding.get("description") or "").lower()
        severity = (finding.get("severity") or "").lower()

        matches: list[ObligationMatch] = []

        for obligation in self._obligations:
            if not _severity_meets_threshold(severity, obligation.severity_threshold):
                continue

            category_hits = tuple(
                cond for cond in obligation.trigger_conditions if cond in category
            )
            title_hits = tuple(
                cond for cond in obligation.trigger_conditions
                if cond in title or cond in description
            )

            if category_hits:
                matches.append(
                    ObligationMatch(
                        article_id=obligation.article_id,
                        article_number=obligation.article_number,
                        obligation_text=obligation.obligation_text,
                        match_type="exact",
                        confidence="High",
                        matched_conditions=category_hits,
                    )
                )
            elif title_hits:
                matches.append(
                    ObligationMatch(
                        article_id=obligation.article_id,
                        article_number=obligation.article_number,
                        obligation_text=obligation.obligation_text,
                        match_type="partial",
                        confidence="Medium",
                        matched_conditions=title_hits,
                    )
                )

        return sorted(matches, key=lambda m: m.article_id)

    def get_obligation(self, article_id: str) -> CsdddObligation | None:
        """Look up an obligation by its stable article_id."""
        return _OBLIGATIONS_BY_ID.get(article_id)

    @property
    def obligation_count(self) -> int:
        return len(self._obligations)
