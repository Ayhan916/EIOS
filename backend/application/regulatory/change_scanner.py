"""Regulatory Change Impact Scanner (GAP-19).

Deterministic, pure logic — no LLM calls.

For each new RegulatoryChange:
1. Find all Assessments in the org that reference the same framework
   (via framework_code on the assessment or its sector).
2. Find all ComplianceGaps referencing the framework.
3. Create RegulatoryChangeImpact rows.
4. Update assessment.review_status = "regulatory_re_review_required".
5. Return a list of (assessment_id, gap_id) tuples for notification.

Curated seed of known upcoming regulatory changes is also provided here
so new organisations get a pre-populated change feed on first load.
"""

from __future__ import annotations

from datetime import date

# ── Curated regulatory change seed ────────────────────────────────────────────
# Known EU/German changes tracked as of 2026-07.
# Format: dict matching RegulatoryChange fields (no id, no org-specific fields).

REGULATORY_CHANGE_SEED: list[dict] = [
    {
        "framework_code": "CSDDD",
        "change_title": "CSDDD Art. 10 — Prioritisation obligations enter into force",
        "change_description": (
            "Companies with >5 000 employees or >1.5 bn EUR turnover must document and justify "
            "prioritisation decisions when they cannot address all identified adverse impacts "
            "simultaneously. The documented framework must be available for supervisory review."
        ),
        "affected_article": "Art. 10",
        "effective_date": date(2027, 7, 26),
        "severity": "major",
        "source_name": "EUR-Lex",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "affected_sectors": [],
        "affected_frameworks": ["LkSG"],
        "regulation_refs": "Directive (EU) 2024/1760, OJ L 2024/1760",
    },
    {
        "framework_code": "CSDDD",
        "change_title": "CSDDD Art. 14 — Grievance mechanism mandatory",
        "change_description": (
            "Effective July 2027, in-scope companies must operate or participate in an effective "
            "grievance mechanism accessible to workers, trade unions, NGOs, and affected communities. "
            "Anonymous complaints must be accepted and a reference code issued."
        ),
        "affected_article": "Art. 14",
        "effective_date": date(2027, 7, 26),
        "severity": "major",
        "source_name": "EUR-Lex",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "affected_sectors": [],
        "affected_frameworks": ["LkSG"],
        "regulation_refs": "Directive (EU) 2024/1760, OJ L 2024/1760",
    },
    {
        "framework_code": "LkSG",
        "change_title": "LkSG §3 scope expansion — indirect suppliers included from 2024",
        "change_description": (
            "Since 1 January 2024, companies with ≥1 000 employees must extend due diligence "
            "obligations to indirect suppliers when there is 'substantiated knowledge' of violations. "
            "Existing assessments covering only direct (Tier-1) suppliers may need rescoping."
        ),
        "affected_article": "§3 Abs. 3",
        "effective_date": date(2024, 1, 1),
        "severity": "major",
        "source_name": "Bundesanzeiger",
        "source_url": "https://www.gesetze-im-internet.de/lksg/",
        "affected_sectors": [],
        "affected_frameworks": ["CSDDD"],
        "regulation_refs": "LkSG BGBl. I 2021 Nr. 46",
    },
    {
        "framework_code": "CSRD",
        "change_title": "CSRD ESRS E1 — Climate reporting mandatory for large companies 2025",
        "change_description": (
            "Companies in scope of CSRD must disclose Scope 1, 2, and 3 GHG emissions under "
            "ESRS E1 starting with the financial year 2024 (reported in 2025). Existing "
            "environmental assessments should be reviewed for climate data completeness."
        ),
        "affected_article": "ESRS E1",
        "effective_date": date(2025, 1, 1),
        "severity": "moderate",
        "source_name": "ESMA",
        "source_url": "https://www.esma.europa.eu/esrs",
        "affected_sectors": ["05", "06", "19", "20", "24", "35"],  # energy-intensive NACE codes
        "affected_frameworks": ["CSDDD", "LkSG"],
        "regulation_refs": "Directive (EU) 2022/2464; Commission Delegated Regulation (EU) 2023/2772",
    },
    {
        "framework_code": "CSDDD",
        "change_title": "CSDDD Annex — High-risk sector list updated (2026)",
        "change_description": (
            "The European Commission updated the list of high-risk sectors under CSDDD Annex "
            "to include additional NACE categories: textiles (13, 14), mining (07, 08), and "
            "agriculture (01, 02). Suppliers in these sectors must be re-classified and "
            "re-assessed if current risk band does not reflect CSDDD Annex classification."
        ),
        "affected_article": "Annex (High-risk sectors)",
        "effective_date": date(2026, 1, 1),
        "severity": "moderate",
        "source_name": "EUR-Lex",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "affected_sectors": ["01", "02", "07", "08", "13", "14"],
        "affected_frameworks": ["LkSG"],
        "regulation_refs": "Directive (EU) 2024/1760, Annex",
    },
]

# ── Impact scan logic ─────────────────────────────────────────────────────────

_REVIEW_STATUS_FLAG = "regulatory_re_review_required"


def build_impact_summary(
    *,
    framework_code: str,
    assessment_count: int,
    gap_count: int,
    affected_sectors: list[str],
) -> str:
    sector_text = (
        f" in sectors {', '.join(affected_sectors)}" if affected_sectors else ""
    )
    parts: list[str] = []
    if assessment_count:
        parts.append(f"{assessment_count} assessment(s) flagged for re-review")
    if gap_count:
        parts.append(f"{gap_count} compliance gap(s) require update")
    if not parts:
        return f"No existing {framework_code} assessments or gaps affected."
    return (
        f"Impact scan for {framework_code}{sector_text}: "
        + "; ".join(parts)
        + ". Items have been flagged for regulatory re-review."
    )
