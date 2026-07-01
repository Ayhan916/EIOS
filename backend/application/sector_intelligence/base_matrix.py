"""
CSDDD Sector Risk Register — Static Base Matrix (TASK-003 Phase 2)

Curated probability scores (1–10) per NACE 2-digit sector × CSDDD protected right.
  1  = Very unlikely (structural absence of risk)
  5  = Moderate (sector has some inherent exposure)
  10 = Near-certain (systemic, documented, pervasive risk)

Sources used for calibration:
  - CSDDD Annex I (primary rights catalogue)
  - ILO Sector-specific Labour Reports (2022–2024)
  - OECD Due Diligence Guidance for Responsible Supply Chains (2023)
  - Know The Chain Benchmark Reports: Textiles, Electronics, Food (2023)
  - Business & Human Rights Resource Centre sector profiles
  - Transparency International CPI (governance proxy for corruption risk)

Calibration version: v1.0 (2026-07-01)
Approval: Founder — 2026-07-01
Next review: 2027-01-01

IMPORTANT: These scores are static and human-approved (M43 compliant).
Do NOT generate or modify scores programmatically without human approval.
Changes must go through the RAG calibration pipeline + Founder sign-off.
"""

from __future__ import annotations

from domain.enums import CSDDDRight

# ---------------------------------------------------------------------------
# Type alias for readability
# ---------------------------------------------------------------------------
_R = CSDDDRight
_Score = dict[CSDDDRight, int]

# ---------------------------------------------------------------------------
# Base matrix: nace_2digit → {CSDDDRight → probability 1-10}
# ---------------------------------------------------------------------------
BASE_MATRIX: dict[str, _Score] = {

    # ── NACE 01: Agriculture, crop and animal production ──────────────────
    # Highest-risk sector globally for labour and environmental rights.
    # ILO: 170M child labourers worldwide in agriculture (58% of total).
    "01": {
        _R.CHILD_LABOUR: 9,
        _R.FORCED_LABOUR: 8,
        _R.FREEDOM_OF_ASSOCIATION: 7,
        _R.COLLECTIVE_BARGAINING: 7,
        _R.DISCRIMINATION: 6,
        _R.MINIMUM_WAGE: 8,
        _R.WORKING_HOURS: 8,
        _R.OCCUPATIONAL_SAFETY: 7,
        _R.LAND_RIGHTS: 8,
        _R.WATER_RIGHTS: 8,
        _R.ENVIRONMENTAL_DESTRUCTION: 8,
        _R.HARMFUL_CHEMICALS: 8,
        _R.BIODIVERSITY: 8,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 4,
        _R.HUMAN_DIGNITY: 6,
        _R.MODERN_SLAVERY: 7,
        _R.MIGRANT_WORKER_RIGHTS: 8,
        _R.COMMUNITY_RIGHTS: 7,
    },

    # ── NACE 05: Mining of coal and lignite ───────────────────────────────
    # Artisanal and small-scale mining: severe child/forced labour.
    # Significant environmental destruction and community displacement.
    "05": {
        _R.CHILD_LABOUR: 7,
        _R.FORCED_LABOUR: 8,
        _R.FREEDOM_OF_ASSOCIATION: 6,
        _R.COLLECTIVE_BARGAINING: 6,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 6,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 9,
        _R.LAND_RIGHTS: 8,
        _R.WATER_RIGHTS: 7,
        _R.ENVIRONMENTAL_DESTRUCTION: 9,
        _R.HARMFUL_CHEMICALS: 7,
        _R.BIODIVERSITY: 8,
        _R.MERCURY: 5,
        _R.HAZARDOUS_WASTE: 7,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 5,
        _R.HUMAN_DIGNITY: 6,
        _R.MODERN_SLAVERY: 7,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 8,
    },

    # ── NACE 07: Mining of metal ores ─────────────────────────────────────
    # Cobalt (DRC), lithium (Bolivia/Chile), gold: child labour documented.
    # Mercury use in artisanal gold mining is systemic.
    "07": {
        _R.CHILD_LABOUR: 8,
        _R.FORCED_LABOUR: 8,
        _R.FREEDOM_OF_ASSOCIATION: 6,
        _R.COLLECTIVE_BARGAINING: 6,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 6,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 9,
        _R.LAND_RIGHTS: 9,
        _R.WATER_RIGHTS: 8,
        _R.ENVIRONMENTAL_DESTRUCTION: 9,
        _R.HARMFUL_CHEMICALS: 8,
        _R.BIODIVERSITY: 9,
        _R.MERCURY: 8,
        _R.HAZARDOUS_WASTE: 8,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 5,
        _R.HUMAN_DIGNITY: 7,
        _R.MODERN_SLAVERY: 8,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 9,
    },

    # ── NACE 10: Manufacture of food products ─────────────────────────────
    # Migrant workers, seasonal labour, cold chain safety risks.
    "10": {
        _R.CHILD_LABOUR: 6,
        _R.FORCED_LABOUR: 6,
        _R.FREEDOM_OF_ASSOCIATION: 6,
        _R.COLLECTIVE_BARGAINING: 6,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 7,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 6,
        _R.LAND_RIGHTS: 4,
        _R.WATER_RIGHTS: 6,
        _R.ENVIRONMENTAL_DESTRUCTION: 6,
        _R.HARMFUL_CHEMICALS: 6,
        _R.BIODIVERSITY: 5,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 4,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 5,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 4,
    },

    # ── NACE 13: Manufacture of textiles ──────────────────────────────────
    # KnowTheChain 2023: worst performer for forced labour in manufacturing.
    # Documented: Xinjiang cotton, Bangladesh factory conditions.
    "13": {
        _R.CHILD_LABOUR: 8,
        _R.FORCED_LABOUR: 9,
        _R.FREEDOM_OF_ASSOCIATION: 8,
        _R.COLLECTIVE_BARGAINING: 8,
        _R.DISCRIMINATION: 7,
        _R.MINIMUM_WAGE: 8,
        _R.WORKING_HOURS: 8,
        _R.OCCUPATIONAL_SAFETY: 7,
        _R.LAND_RIGHTS: 3,
        _R.WATER_RIGHTS: 7,
        _R.ENVIRONMENTAL_DESTRUCTION: 7,
        _R.HARMFUL_CHEMICALS: 7,
        _R.BIODIVERSITY: 4,
        _R.MERCURY: 2,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 5,
        _R.HUMAN_DIGNITY: 7,
        _R.MODERN_SLAVERY: 8,
        _R.MIGRANT_WORKER_RIGHTS: 8,
        _R.COMMUNITY_RIGHTS: 4,
    },

    # ── NACE 14: Manufacture of wearing apparel ───────────────────────────
    # Similar to textiles but even higher concentration in at-risk countries.
    "14": {
        _R.CHILD_LABOUR: 8,
        _R.FORCED_LABOUR: 9,
        _R.FREEDOM_OF_ASSOCIATION: 8,
        _R.COLLECTIVE_BARGAINING: 8,
        _R.DISCRIMINATION: 7,
        _R.MINIMUM_WAGE: 8,
        _R.WORKING_HOURS: 9,
        _R.OCCUPATIONAL_SAFETY: 7,
        _R.LAND_RIGHTS: 2,
        _R.WATER_RIGHTS: 5,
        _R.ENVIRONMENTAL_DESTRUCTION: 6,
        _R.HARMFUL_CHEMICALS: 6,
        _R.BIODIVERSITY: 3,
        _R.MERCURY: 2,
        _R.HAZARDOUS_WASTE: 4,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 5,
        _R.HUMAN_DIGNITY: 7,
        _R.MODERN_SLAVERY: 9,
        _R.MIGRANT_WORKER_RIGHTS: 9,
        _R.COMMUNITY_RIGHTS: 3,
    },

    # ── NACE 20: Manufacture of chemicals ────────────────────────────────
    # Hazardous chemicals, waste disposal, occupational health.
    "20": {
        _R.CHILD_LABOUR: 3,
        _R.FORCED_LABOUR: 4,
        _R.FREEDOM_OF_ASSOCIATION: 4,
        _R.COLLECTIVE_BARGAINING: 4,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 5,
        _R.OCCUPATIONAL_SAFETY: 8,
        _R.LAND_RIGHTS: 4,
        _R.WATER_RIGHTS: 7,
        _R.ENVIRONMENTAL_DESTRUCTION: 8,
        _R.HARMFUL_CHEMICALS: 9,
        _R.BIODIVERSITY: 6,
        _R.MERCURY: 6,
        _R.HAZARDOUS_WASTE: 9,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 2,
        _R.HUMAN_DIGNITY: 4,
        _R.MODERN_SLAVERY: 3,
        _R.MIGRANT_WORKER_RIGHTS: 4,
        _R.COMMUNITY_RIGHTS: 5,
    },

    # ── NACE 23: Manufacture of non-metallic mineral products (cement) ────
    # Dust, silicosis, environmental pollution. Child labour in brick kilns.
    "23": {
        _R.CHILD_LABOUR: 6,
        _R.FORCED_LABOUR: 5,
        _R.FREEDOM_OF_ASSOCIATION: 5,
        _R.COLLECTIVE_BARGAINING: 5,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 5,
        _R.WORKING_HOURS: 6,
        _R.OCCUPATIONAL_SAFETY: 8,
        _R.LAND_RIGHTS: 6,
        _R.WATER_RIGHTS: 5,
        _R.ENVIRONMENTAL_DESTRUCTION: 7,
        _R.HARMFUL_CHEMICALS: 6,
        _R.BIODIVERSITY: 6,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 6,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 5,
        _R.MIGRANT_WORKER_RIGHTS: 6,
        _R.COMMUNITY_RIGHTS: 6,
    },

    # ── NACE 24: Manufacture of basic metals ─────────────────────────────
    # Steel, aluminium, copper: high environmental impact. Safety-critical.
    "24": {
        _R.CHILD_LABOUR: 4,
        _R.FORCED_LABOUR: 5,
        _R.FREEDOM_OF_ASSOCIATION: 5,
        _R.COLLECTIVE_BARGAINING: 5,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 6,
        _R.OCCUPATIONAL_SAFETY: 8,
        _R.LAND_RIGHTS: 5,
        _R.WATER_RIGHTS: 6,
        _R.ENVIRONMENTAL_DESTRUCTION: 8,
        _R.HARMFUL_CHEMICALS: 7,
        _R.BIODIVERSITY: 6,
        _R.MERCURY: 5,
        _R.HAZARDOUS_WASTE: 7,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 4,
        _R.MODERN_SLAVERY: 4,
        _R.MIGRANT_WORKER_RIGHTS: 5,
        _R.COMMUNITY_RIGHTS: 6,
    },

    # ── NACE 26: Manufacture of electronics ──────────────────────────────
    # KnowTheChain: electronics ranks poorly on forced labour disclosure.
    # Conflict minerals (tin, tantalum, tungsten, gold) in supply chain.
    "26": {
        _R.CHILD_LABOUR: 7,
        _R.FORCED_LABOUR: 8,
        _R.FREEDOM_OF_ASSOCIATION: 7,
        _R.COLLECTIVE_BARGAINING: 7,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 6,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 6,
        _R.LAND_RIGHTS: 5,
        _R.WATER_RIGHTS: 5,
        _R.ENVIRONMENTAL_DESTRUCTION: 6,
        _R.HARMFUL_CHEMICALS: 7,
        _R.BIODIVERSITY: 5,
        _R.MERCURY: 4,
        _R.HAZARDOUS_WASTE: 7,
        _R.PRIVACY: 4,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 7,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 5,
    },

    # ── NACE 28: Manufacture of machinery and equipment ───────────────────
    "28": {
        _R.CHILD_LABOUR: 3,
        _R.FORCED_LABOUR: 4,
        _R.FREEDOM_OF_ASSOCIATION: 4,
        _R.COLLECTIVE_BARGAINING: 4,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 5,
        _R.OCCUPATIONAL_SAFETY: 6,
        _R.LAND_RIGHTS: 3,
        _R.WATER_RIGHTS: 4,
        _R.ENVIRONMENTAL_DESTRUCTION: 5,
        _R.HARMFUL_CHEMICALS: 5,
        _R.BIODIVERSITY: 3,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 2,
        _R.HUMAN_DIGNITY: 3,
        _R.MODERN_SLAVERY: 3,
        _R.MIGRANT_WORKER_RIGHTS: 4,
        _R.COMMUNITY_RIGHTS: 3,
    },

    # ── NACE 29: Manufacture of motor vehicles ────────────────────────────
    # Catena-X core sector. Tier-N supply chains in high-risk countries.
    # Direct operations: safer. Deep supply chain: minerals, textiles, rubber.
    "29": {
        _R.CHILD_LABOUR: 3,
        _R.FORCED_LABOUR: 4,
        _R.FREEDOM_OF_ASSOCIATION: 5,
        _R.COLLECTIVE_BARGAINING: 5,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 5,
        _R.OCCUPATIONAL_SAFETY: 6,
        _R.LAND_RIGHTS: 3,
        _R.WATER_RIGHTS: 4,
        _R.ENVIRONMENTAL_DESTRUCTION: 6,
        _R.HARMFUL_CHEMICALS: 6,
        _R.BIODIVERSITY: 4,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 6,
        _R.PRIVACY: 3,
        _R.FREEDOM_OF_EXPRESSION: 2,
        _R.HUMAN_DIGNITY: 3,
        _R.MODERN_SLAVERY: 4,
        _R.MIGRANT_WORKER_RIGHTS: 4,
        _R.COMMUNITY_RIGHTS: 3,
    },

    # ── NACE 35: Electricity and gas supply ──────────────────────────────
    # Large infrastructure projects: community displacement, land rights.
    "35": {
        _R.CHILD_LABOUR: 2,
        _R.FORCED_LABOUR: 3,
        _R.FREEDOM_OF_ASSOCIATION: 4,
        _R.COLLECTIVE_BARGAINING: 4,
        _R.DISCRIMINATION: 3,
        _R.MINIMUM_WAGE: 3,
        _R.WORKING_HOURS: 4,
        _R.OCCUPATIONAL_SAFETY: 7,
        _R.LAND_RIGHTS: 6,
        _R.WATER_RIGHTS: 5,
        _R.ENVIRONMENTAL_DESTRUCTION: 7,
        _R.HARMFUL_CHEMICALS: 5,
        _R.BIODIVERSITY: 6,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 3,
        _R.MODERN_SLAVERY: 3,
        _R.MIGRANT_WORKER_RIGHTS: 4,
        _R.COMMUNITY_RIGHTS: 6,
    },

    # ── NACE 41: Construction of buildings ───────────────────────────────
    # High migrant worker population globally. Safety accident rates high.
    "41": {
        _R.CHILD_LABOUR: 5,
        _R.FORCED_LABOUR: 6,
        _R.FREEDOM_OF_ASSOCIATION: 5,
        _R.COLLECTIVE_BARGAINING: 5,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 6,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 8,
        _R.LAND_RIGHTS: 5,
        _R.WATER_RIGHTS: 4,
        _R.ENVIRONMENTAL_DESTRUCTION: 5,
        _R.HARMFUL_CHEMICALS: 5,
        _R.BIODIVERSITY: 4,
        _R.MERCURY: 2,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 2,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 6,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 4,
    },

    # ── NACE 46: Wholesale trade ──────────────────────────────────────────
    # Lower direct risk; depends on sourcing practices of supply chain.
    "46": {
        _R.CHILD_LABOUR: 3,
        _R.FORCED_LABOUR: 4,
        _R.FREEDOM_OF_ASSOCIATION: 3,
        _R.COLLECTIVE_BARGAINING: 3,
        _R.DISCRIMINATION: 3,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 4,
        _R.OCCUPATIONAL_SAFETY: 4,
        _R.LAND_RIGHTS: 2,
        _R.WATER_RIGHTS: 2,
        _R.ENVIRONMENTAL_DESTRUCTION: 3,
        _R.HARMFUL_CHEMICALS: 3,
        _R.BIODIVERSITY: 2,
        _R.MERCURY: 1,
        _R.HAZARDOUS_WASTE: 3,
        _R.PRIVACY: 3,
        _R.FREEDOM_OF_EXPRESSION: 2,
        _R.HUMAN_DIGNITY: 3,
        _R.MODERN_SLAVERY: 4,
        _R.MIGRANT_WORKER_RIGHTS: 4,
        _R.COMMUNITY_RIGHTS: 2,
    },

    # ── NACE 49: Land transport and logistics ────────────────────────────
    # Long-haul trucking: forced labour, excessive hours, migrant drivers.
    # OECD: road freight identified as high-risk for labour exploitation.
    "49": {
        _R.CHILD_LABOUR: 2,
        _R.FORCED_LABOUR: 6,
        _R.FREEDOM_OF_ASSOCIATION: 5,
        _R.COLLECTIVE_BARGAINING: 5,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 5,
        _R.WORKING_HOURS: 8,
        _R.OCCUPATIONAL_SAFETY: 7,
        _R.LAND_RIGHTS: 2,
        _R.WATER_RIGHTS: 2,
        _R.ENVIRONMENTAL_DESTRUCTION: 5,
        _R.HARMFUL_CHEMICALS: 3,
        _R.BIODIVERSITY: 2,
        _R.MERCURY: 1,
        _R.HAZARDOUS_WASTE: 3,
        _R.PRIVACY: 3,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 6,
        _R.MIGRANT_WORKER_RIGHTS: 7,
        _R.COMMUNITY_RIGHTS: 2,
    },

    # ── NACE 62: IT / Software / Computer programming ─────────────────────
    # Lowest inherent CSDDD risk. Data privacy most relevant.
    "62": {
        _R.CHILD_LABOUR: 1,
        _R.FORCED_LABOUR: 1,
        _R.FREEDOM_OF_ASSOCIATION: 3,
        _R.COLLECTIVE_BARGAINING: 3,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 2,
        _R.WORKING_HOURS: 4,
        _R.OCCUPATIONAL_SAFETY: 2,
        _R.LAND_RIGHTS: 1,
        _R.WATER_RIGHTS: 1,
        _R.ENVIRONMENTAL_DESTRUCTION: 2,
        _R.HARMFUL_CHEMICALS: 1,
        _R.BIODIVERSITY: 1,
        _R.MERCURY: 1,
        _R.HAZARDOUS_WASTE: 1,
        _R.PRIVACY: 7,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 2,
        _R.MODERN_SLAVERY: 1,
        _R.MIGRANT_WORKER_RIGHTS: 3,
        _R.COMMUNITY_RIGHTS: 1,
    },

    # ── NACE 70: Management consultancy ──────────────────────────────────
    "70": {
        _R.CHILD_LABOUR: 1,
        _R.FORCED_LABOUR: 1,
        _R.FREEDOM_OF_ASSOCIATION: 3,
        _R.COLLECTIVE_BARGAINING: 3,
        _R.DISCRIMINATION: 4,
        _R.MINIMUM_WAGE: 2,
        _R.WORKING_HOURS: 4,
        _R.OCCUPATIONAL_SAFETY: 2,
        _R.LAND_RIGHTS: 1,
        _R.WATER_RIGHTS: 1,
        _R.ENVIRONMENTAL_DESTRUCTION: 2,
        _R.HARMFUL_CHEMICALS: 1,
        _R.BIODIVERSITY: 1,
        _R.MERCURY: 1,
        _R.HAZARDOUS_WASTE: 1,
        _R.PRIVACY: 5,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 2,
        _R.MODERN_SLAVERY: 1,
        _R.MIGRANT_WORKER_RIGHTS: 2,
        _R.COMMUNITY_RIGHTS: 1,
    },

    # ── NACE 78: Employment activities (staffing agencies) ────────────────
    # Temporary work agencies: labour exploitation, wage theft.
    "78": {
        _R.CHILD_LABOUR: 4,
        _R.FORCED_LABOUR: 6,
        _R.FREEDOM_OF_ASSOCIATION: 6,
        _R.COLLECTIVE_BARGAINING: 6,
        _R.DISCRIMINATION: 6,
        _R.MINIMUM_WAGE: 7,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 5,
        _R.LAND_RIGHTS: 1,
        _R.WATER_RIGHTS: 1,
        _R.ENVIRONMENTAL_DESTRUCTION: 2,
        _R.HARMFUL_CHEMICALS: 2,
        _R.BIODIVERSITY: 1,
        _R.MERCURY: 1,
        _R.HAZARDOUS_WASTE: 1,
        _R.PRIVACY: 4,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 6,
        _R.MODERN_SLAVERY: 7,
        _R.MIGRANT_WORKER_RIGHTS: 8,
        _R.COMMUNITY_RIGHTS: 2,
    },

    # ── NACE 86: Human health activities ─────────────────────────────────
    "86": {
        _R.CHILD_LABOUR: 1,
        _R.FORCED_LABOUR: 2,
        _R.FREEDOM_OF_ASSOCIATION: 4,
        _R.COLLECTIVE_BARGAINING: 4,
        _R.DISCRIMINATION: 5,
        _R.MINIMUM_WAGE: 4,
        _R.WORKING_HOURS: 7,
        _R.OCCUPATIONAL_SAFETY: 6,
        _R.LAND_RIGHTS: 1,
        _R.WATER_RIGHTS: 2,
        _R.ENVIRONMENTAL_DESTRUCTION: 3,
        _R.HARMFUL_CHEMICALS: 5,
        _R.BIODIVERSITY: 1,
        _R.MERCURY: 3,
        _R.HAZARDOUS_WASTE: 5,
        _R.PRIVACY: 8,
        _R.FREEDOM_OF_EXPRESSION: 3,
        _R.HUMAN_DIGNITY: 5,
        _R.MODERN_SLAVERY: 2,
        _R.MIGRANT_WORKER_RIGHTS: 5,
        _R.COMMUNITY_RIGHTS: 2,
    },
}

# ---------------------------------------------------------------------------
# Fallback scores for NACE codes not in the matrix
# Based on global averages from ILO 2024 World Employment and Social Outlook
# ---------------------------------------------------------------------------
_FALLBACK_SCORES: _Score = {
    _R.CHILD_LABOUR: 4,
    _R.FORCED_LABOUR: 4,
    _R.FREEDOM_OF_ASSOCIATION: 4,
    _R.COLLECTIVE_BARGAINING: 4,
    _R.DISCRIMINATION: 4,
    _R.MINIMUM_WAGE: 4,
    _R.WORKING_HOURS: 4,
    _R.OCCUPATIONAL_SAFETY: 5,
    _R.LAND_RIGHTS: 3,
    _R.WATER_RIGHTS: 3,
    _R.ENVIRONMENTAL_DESTRUCTION: 4,
    _R.HARMFUL_CHEMICALS: 4,
    _R.BIODIVERSITY: 3,
    _R.MERCURY: 2,
    _R.HAZARDOUS_WASTE: 3,
    _R.PRIVACY: 3,
    _R.FREEDOM_OF_EXPRESSION: 3,
    _R.HUMAN_DIGNITY: 4,
    _R.MODERN_SLAVERY: 4,
    _R.MIGRANT_WORKER_RIGHTS: 4,
    _R.COMMUNITY_RIGHTS: 3,
}

CALIBRATION_VERSION = "v1.0"
CALIBRATION_DATE = "2026-07-01"
CALIBRATION_APPROVED_BY = "Founder"


def get_scores(nace_2digit: str) -> _Score:
    """Return the approved base scores for a NACE 2-digit code.

    Falls back to global averages if the sector is not yet calibrated.
    Always returns a copy — callers must not mutate the base matrix.
    """
    return dict(BASE_MATRIX.get(nace_2digit.strip().zfill(2), _FALLBACK_SCORES))


def get_score(nace_2digit: str, right: CSDDDRight) -> int:
    """Return the approved probability score for one sector × right pair."""
    return get_scores(nace_2digit).get(right, _FALLBACK_SCORES[right])


def is_calibrated(nace_2digit: str) -> bool:
    """Return True if this NACE code has a curated entry in the base matrix."""
    return nace_2digit.strip().zfill(2) in BASE_MATRIX


CALIBRATED_NACE_CODES: list[str] = sorted(BASE_MATRIX.keys())
