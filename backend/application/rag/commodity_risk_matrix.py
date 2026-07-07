"""Commodity Risk Matrix — deterministisch, M43-konform.

Analogon zur BASE_MATRIX im SimulationEngine, aber für Rohstofflieferanten.
Keyed by commodity_code × scenario_type → CSDDD-Right-Scores (0–10).

Baseline = typisches Risikoprofil ohne Szenario.
Scenario-Delta = zusätzliche Verschlechterung durch das Szenario.
"""

from __future__ import annotations

# ── Baseline-Scores pro Rohstoff (0–10, höher = höheres Risiko) ──────────────
# Quellen: OECD Due Diligence Minerals, UN Environment, ILRF, KnowTheChain

COMMODITY_BASELINE: dict[str, dict[str, float]] = {
    "cobalt": {
        # Kobalt: v.a. DRC — Kinderarbeit im Artisanal Mining (ASM) gut dokumentiert
        "child_labour":              8.5,
        "forced_labour":             7.0,
        "modern_slavery":            7.0,
        "occupational_safety":       8.0,
        "land_rights":               7.5,
        "water_rights":              7.0,
        "environmental_destruction": 7.5,
        "harmful_chemicals":         6.5,
        "hazardous_waste":           7.0,
        "biodiversity":              6.5,
        "community_rights":          7.5,
        "human_dignity":             7.0,
        "migrant_worker_rights":     6.0,
        "discrimination":            5.5,
        "minimum_wage":              6.5,
        "working_hours":             7.0,
        "freedom_of_association":    5.0,
        "collective_bargaining":     4.5,
        "mercury":                   3.0,
        "privacy":                   2.0,
        "freedom_of_expression":     3.0,
    },
    "lithium": {
        # Lithium: Atacama/DRC/Australien — Wasserknappheit, Landrechte indigener Gemeinschaften
        "child_labour":              4.5,
        "forced_labour":             3.5,
        "modern_slavery":            3.5,
        "occupational_safety":       6.0,
        "land_rights":               8.5,
        "water_rights":              9.0,
        "environmental_destruction": 8.0,
        "harmful_chemicals":         6.0,
        "hazardous_waste":           5.5,
        "biodiversity":              7.5,
        "community_rights":          8.5,
        "human_dignity":             5.0,
        "migrant_worker_rights":     4.5,
        "discrimination":            4.5,
        "minimum_wage":              5.0,
        "working_hours":             5.5,
        "freedom_of_association":    4.0,
        "collective_bargaining":     3.5,
        "mercury":                   2.0,
        "privacy":                   2.0,
        "freedom_of_expression":     2.5,
    },
    "copper": {
        # Kupfer: Chile, Kongo, Peru — Arbeitssicherheit, Umweltzerstörung, Gemeinschaft
        "child_labour":              5.0,
        "forced_labour":             4.5,
        "modern_slavery":            4.5,
        "occupational_safety":       7.5,
        "land_rights":               7.0,
        "water_rights":              7.5,
        "environmental_destruction": 8.0,
        "harmful_chemicals":         7.0,
        "hazardous_waste":           7.5,
        "biodiversity":              7.0,
        "community_rights":          7.0,
        "human_dignity":             5.5,
        "migrant_worker_rights":     5.5,
        "discrimination":            4.5,
        "minimum_wage":              5.5,
        "working_hours":             6.0,
        "freedom_of_association":    5.5,
        "collective_bargaining":     5.0,
        "mercury":                   4.0,
        "privacy":                   2.0,
        "freedom_of_expression":     3.0,
    },
    "cotton": {
        # Baumwolle: Usbekistan, China (Xinjiang), Indien — Zwangsarbeit, Kinderarbeit, Pestizide
        "child_labour":              7.5,
        "forced_labour":             8.5,
        "modern_slavery":            8.0,
        "occupational_safety":       6.5,
        "land_rights":               5.5,
        "water_rights":              8.0,
        "environmental_destruction": 6.5,
        "harmful_chemicals":         8.5,
        "hazardous_waste":           5.0,
        "biodiversity":              6.0,
        "community_rights":          6.0,
        "human_dignity":             7.0,
        "migrant_worker_rights":     7.5,
        "discrimination":            7.0,
        "minimum_wage":              7.5,
        "working_hours":             7.5,
        "freedom_of_association":    6.5,
        "collective_bargaining":     5.5,
        "mercury":                   2.0,
        "privacy":                   4.0,
        "freedom_of_expression":     5.5,
    },
    "soy": {
        # Soja: Brasilien, Argentinien — Landrechte, Abholzung, Gemeinschaft, Biodiversität
        "child_labour":              5.5,
        "forced_labour":             5.5,
        "modern_slavery":            5.0,
        "occupational_safety":       5.5,
        "land_rights":               8.5,
        "water_rights":              6.5,
        "environmental_destruction": 9.0,
        "harmful_chemicals":         7.0,
        "hazardous_waste":           4.5,
        "biodiversity":              9.0,
        "community_rights":          8.0,
        "human_dignity":             5.5,
        "migrant_worker_rights":     6.0,
        "discrimination":            5.0,
        "minimum_wage":              6.0,
        "working_hours":             6.0,
        "freedom_of_association":    5.0,
        "collective_bargaining":     4.5,
        "mercury":                   2.0,
        "privacy":                   2.0,
        "freedom_of_expression":     3.5,
    },
    "palm_oil": {
        # Palmöl: Indonesien, Malaysia — Regenwald, Landrechte, Kinderarbeit auf Plantagen
        "child_labour":              7.0,
        "forced_labour":             6.5,
        "modern_slavery":            6.5,
        "occupational_safety":       6.0,
        "land_rights":               9.0,
        "water_rights":              6.0,
        "environmental_destruction": 9.5,
        "harmful_chemicals":         6.5,
        "hazardous_waste":           5.0,
        "biodiversity":              9.5,
        "community_rights":          8.5,
        "human_dignity":             6.5,
        "migrant_worker_rights":     7.5,
        "discrimination":            6.0,
        "minimum_wage":              6.5,
        "working_hours":             7.0,
        "freedom_of_association":    5.5,
        "collective_bargaining":     4.5,
        "mercury":                   2.0,
        "privacy":                   2.5,
        "freedom_of_expression":     4.0,
    },
}

# ── Szenario-Deltas (zusätzliche Punkte auf Baseline, capped bei 10) ──────────
# Format: scenario_type → commodity_code → right_id → delta

COMMODITY_SCENARIO_DELTA: dict[str, dict[str, dict[str, float]]] = {
    "geopolitical_conflict": {
        "cobalt":    {"forced_labour": 2.0, "modern_slavery": 1.5, "child_labour": 1.0, "community_rights": 1.0},
        "lithium":   {"land_rights": 2.0, "community_rights": 2.0, "water_rights": 1.0},
        "copper":    {"occupational_safety": 1.5, "community_rights": 1.5, "environmental_destruction": 1.0},
        "cotton":    {"forced_labour": 2.5, "discrimination": 2.0, "freedom_of_expression": 2.0},
        "soy":       {"land_rights": 2.0, "community_rights": 2.0, "environmental_destruction": 1.0},
        "palm_oil":  {"land_rights": 2.0, "community_rights": 2.0, "migrant_worker_rights": 1.5},
    },
    "sanctions_escalation": {
        "cobalt":    {"child_labour": 1.5, "forced_labour": 1.0, "hazardous_waste": 1.0},
        "lithium":   {"water_rights": 1.5, "land_rights": 1.5, "community_rights": 1.0},
        "copper":    {"hazardous_waste": 2.0, "environmental_destruction": 1.5, "water_rights": 1.0},
        "cotton":    {"forced_labour": 2.0, "discrimination": 1.5, "minimum_wage": 1.5},
        "soy":       {"environmental_destruction": 2.0, "biodiversity": 2.0, "land_rights": 1.5},
        "palm_oil":  {"environmental_destruction": 2.0, "biodiversity": 2.0, "land_rights": 1.5},
    },
    "natural_disaster": {
        "cobalt":    {"occupational_safety": 2.5, "hazardous_waste": 2.0, "water_rights": 2.0},
        "lithium":   {"water_rights": 3.0, "environmental_destruction": 2.5, "community_rights": 2.0},
        "copper":    {"occupational_safety": 2.5, "hazardous_waste": 2.5, "environmental_destruction": 2.0},
        "cotton":    {"working_hours": 2.0, "minimum_wage": 1.5, "occupational_safety": 2.0},
        "soy":       {"biodiversity": 2.0, "water_rights": 2.5, "community_rights": 2.0},
        "palm_oil":  {"biodiversity": 2.0, "water_rights": 2.0, "community_rights": 2.0},
    },
    "regulatory_change": {
        "cobalt":    {"hazardous_waste": 2.0, "harmful_chemicals": 1.5, "environmental_destruction": 1.5},
        "lithium":   {"water_rights": 2.0, "environmental_destruction": 2.0, "land_rights": 1.5},
        "copper":    {"hazardous_waste": 2.5, "harmful_chemicals": 2.0, "environmental_destruction": 2.0},
        "cotton":    {"harmful_chemicals": 2.5, "water_rights": 2.0, "biodiversity": 1.5},
        "soy":       {"environmental_destruction": 2.5, "biodiversity": 3.0, "harmful_chemicals": 2.0},
        "palm_oil":  {"environmental_destruction": 3.0, "biodiversity": 3.0, "harmful_chemicals": 2.0},
    },
    "labour_unrest": {
        "cobalt":    {"freedom_of_association": 2.5, "collective_bargaining": 2.5, "minimum_wage": 2.0, "working_hours": 2.0},
        "lithium":   {"freedom_of_association": 2.0, "collective_bargaining": 2.0, "minimum_wage": 1.5},
        "copper":    {"freedom_of_association": 2.5, "collective_bargaining": 2.5, "occupational_safety": 2.0},
        "cotton":    {"freedom_of_association": 2.5, "collective_bargaining": 2.5, "minimum_wage": 2.5, "working_hours": 2.5},
        "soy":       {"freedom_of_association": 2.0, "collective_bargaining": 2.0, "migrant_worker_rights": 2.5},
        "palm_oil":  {"freedom_of_association": 2.5, "collective_bargaining": 2.5, "migrant_worker_rights": 3.0},
    },
    "supply_shortage": {
        "cobalt":    {"child_labour": 2.0, "forced_labour": 2.5, "modern_slavery": 2.0, "occupational_safety": 1.5},
        "lithium":   {"land_rights": 2.5, "water_rights": 2.0, "community_rights": 2.0},
        "copper":    {"occupational_safety": 2.0, "environmental_destruction": 1.5, "hazardous_waste": 1.5},
        "cotton":    {"child_labour": 2.0, "forced_labour": 2.5, "working_hours": 2.0},
        "soy":       {"land_rights": 2.5, "environmental_destruction": 2.5, "biodiversity": 2.0},
        "palm_oil":  {"land_rights": 2.5, "environmental_destruction": 2.5, "biodiversity": 2.5},
    },
}

# Fallback: bei unbekanntem Rohstoff generische moderate Scores
_FALLBACK_BASELINE: dict[str, float] = {right: 5.0 for right in [
    "child_labour", "forced_labour", "freedom_of_association", "collective_bargaining",
    "discrimination", "minimum_wage", "working_hours", "occupational_safety",
    "land_rights", "water_rights", "environmental_destruction", "harmful_chemicals",
    "biodiversity", "mercury", "hazardous_waste", "privacy", "freedom_of_expression",
    "human_dignity", "modern_slavery", "migrant_worker_rights", "community_rights",
]}

_ALL_RIGHTS = list(_FALLBACK_BASELINE.keys())


class CommoditySimulationResult:
    def __init__(
        self,
        commodity_code: str,
        scenario_type: str,
        baseline: dict[str, float],
        adjusted: dict[str, float],
    ):
        self.commodity_code = commodity_code
        self.scenario_type = scenario_type
        self.baseline_scores = baseline
        self.scenario_scores = adjusted
        self.delta = {r: round(adjusted[r] - baseline[r], 2) for r in baseline}


def simulate_commodity(commodity_code: str, scenario_type: str) -> CommoditySimulationResult:
    """Deterministisch: Baseline + Szenario-Delta für einen Rohstofflieferanten."""
    baseline_raw = COMMODITY_BASELINE.get(commodity_code, _FALLBACK_BASELINE)
    baseline = {r: baseline_raw.get(r, 5.0) for r in _ALL_RIGHTS}

    scenario_deltas = COMMODITY_SCENARIO_DELTA.get(scenario_type, {}).get(commodity_code, {})
    adjusted = {
        r: min(10.0, round(baseline[r] + scenario_deltas.get(r, 0.0), 2))
        for r in _ALL_RIGHTS
    }

    return CommoditySimulationResult(
        commodity_code=commodity_code,
        scenario_type=scenario_type,
        baseline=baseline,
        adjusted=adjusted,
    )


# Display-Namen für UI
COMMODITY_DISPLAY: dict[str, str] = {
    "cobalt":    "Kobalt",
    "lithium":   "Lithium",
    "copper":    "Kupfer",
    "cotton":    "Baumwolle",
    "soy":       "Soja",
    "palm_oil":  "Palmöl",
}

COMMODITY_NACE: dict[str, str] = {
    "cobalt":    "B07.29",
    "lithium":   "B07.29",
    "copper":    "B07.29",
    "cotton":    "A01.16",
    "soy":       "A01.11",
    "palm_oil":  "A01.26",
}

COMMODITY_ORIGIN: dict[str, str] = {
    "cobalt":    "DRC, Sambia, Australien",
    "lithium":   "Atacama (Chile/Arg.), DRC, Australien",
    "copper":    "Chile, Peru, DRC, China",
    "cotton":    "Usbekistan, China (Xinjiang), Indien",
    "soy":       "Brasilien, Argentinien, USA",
    "palm_oil":  "Indonesien, Malaysia",
}
