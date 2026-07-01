"""
CSDDD Sector Risk Register — Scenario Simulation Engine (TASK-003 Phase 5)

Applies predefined scenario multipliers to base matrix scores.
100% deterministic: same input → same output, always. No LLM at runtime (M43).

Usage:
    engine = ScenarioSimulationEngine()
    result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from application.sector_intelligence.base_matrix import (
    CALIBRATION_VERSION,
    get_scores,
    is_calibrated,
)
from application.sector_intelligence.nace_taxonomy import (
    NACE_2DIGIT,
    get_division_name,
)
from domain.enums import CSDDDRight, ScenarioType
from domain.sector_risk_register import ScenarioTemplate, SimulationResult


# ---------------------------------------------------------------------------
# Scenario Templates — all factors are static, human-curated, auditable
#
# Factor semantics:
#   1.0  = no change (right not affected by this scenario)
#   1.5  = probability increases by 50% (clamped to max 10)
#   2.0  = probability doubles (clamped to max 10)
#
# Sources: ILO Global Employment and Social Outlook (2024),
#          OECD HRDD Guidance (2023), UN Guiding Principles on Business
#          and Human Rights, academic sector-conflict literature.
# ---------------------------------------------------------------------------

_R = CSDDDRight

_SCENARIO_TEMPLATES: dict[ScenarioType, ScenarioTemplate] = {

    ScenarioType.GEOPOLITICAL_CONFLICT: ScenarioTemplate(
        scenario_type=ScenarioType.GEOPOLITICAL_CONFLICT,
        name="Geopolitischer Konflikt / Kriegsgebiet",
        description=(
            "Armed conflict or active military operations in a producing country "
            "or along key supply chain corridors. Based on ILO 2024 analysis of "
            "labour market deterioration in conflict-affected regions."
        ),
        factors={
            _R.FORCED_LABOUR: 1.5,
            _R.MODERN_SLAVERY: 1.5,
            _R.OCCUPATIONAL_SAFETY: 1.4,
            _R.ENVIRONMENTAL_DESTRUCTION: 1.3,
            _R.MIGRANT_WORKER_RIGHTS: 1.6,
            _R.FREEDOM_OF_EXPRESSION: 1.5,
            _R.FREEDOM_OF_ASSOCIATION: 1.4,
            _R.COMMUNITY_RIGHTS: 1.5,
            _R.LAND_RIGHTS: 1.4,
            _R.HUMAN_DIGNITY: 1.4,
            _R.WATER_RIGHTS: 1.3,
        },
        affected_nace_sections=["A", "B", "C", "H", "F"],
        sources=["ILO 2024 World Employment and Social Outlook", "OECD HRDD Guidance 2023"],
    ),

    ScenarioType.SANCTIONS_ESCALATION: ScenarioTemplate(
        scenario_type=ScenarioType.SANCTIONS_ESCALATION,
        name="Sanktionsverschärfung",
        description=(
            "New or expanded economic sanctions on a country or sector. "
            "Forces supply chain rerouting through less-regulated intermediaries, "
            "increasing forced labour and governance risks."
        ),
        factors={
            _R.FORCED_LABOUR: 1.4,
            _R.MODERN_SLAVERY: 1.3,
            _R.MIGRANT_WORKER_RIGHTS: 1.3,
            _R.FREEDOM_OF_ASSOCIATION: 1.2,
            _R.COLLECTIVE_BARGAINING: 1.2,
            _R.COMMUNITY_RIGHTS: 1.2,
        },
        affected_nace_sections=["B", "C", "G", "H", "K"],
        sources=["OFAC Compliance Framework 2024", "EU Sanctions Implementation Guide"],
    ),

    ScenarioType.NATURAL_DISASTER: ScenarioTemplate(
        scenario_type=ScenarioType.NATURAL_DISASTER,
        name="Naturkatastrophe",
        description=(
            "Flood, earthquake, hurricane, drought, or wildfire affecting "
            "production regions. Acute occupational safety risks; "
            "environmental destruction nearly certain."
        ),
        factors={
            _R.OCCUPATIONAL_SAFETY: 1.8,
            _R.ENVIRONMENTAL_DESTRUCTION: 2.0,
            _R.WATER_RIGHTS: 1.8,
            _R.BIODIVERSITY: 1.7,
            _R.COMMUNITY_RIGHTS: 1.5,
            _R.LAND_RIGHTS: 1.4,
            _R.FORCED_LABOUR: 1.3,
            _R.MIGRANT_WORKER_RIGHTS: 1.4,
            _R.HARMFUL_CHEMICALS: 1.3,
            _R.HAZARDOUS_WASTE: 1.4,
        },
        affected_nace_sections=["A", "B", "C", "D", "E", "F"],
        sources=["UNDRR Global Assessment Report 2023", "ILO Climate Resilience 2024"],
    ),

    ScenarioType.REGULATORY_CHANGE: ScenarioTemplate(
        scenario_type=ScenarioType.REGULATORY_CHANGE,
        name="Regulatorische Verschärfung (CSDDD / LkSG)",
        description=(
            "New mandatory human rights due diligence legislation "
            "(CSDDD, LkSG, CS3D) entering into force. Increases compliance "
            "pressure and surfaces latent risks previously undisclosed."
        ),
        factors={
            _R.CHILD_LABOUR: 1.2,
            _R.FORCED_LABOUR: 1.2,
            _R.OCCUPATIONAL_SAFETY: 1.3,
            _R.ENVIRONMENTAL_DESTRUCTION: 1.5,
            _R.HARMFUL_CHEMICALS: 1.4,
            _R.HAZARDOUS_WASTE: 1.4,
            _R.BIODIVERSITY: 1.3,
            _R.DISCRIMINATION: 1.2,
            _R.FREEDOM_OF_ASSOCIATION: 1.2,
        },
        affected_nace_sections=["A", "B", "C", "G", "H"],
        sources=["CSDDD Directive 2024/1760/EU", "LkSG 2023 Implementation Reports"],
    ),

    ScenarioType.LABOUR_UNREST: ScenarioTemplate(
        scenario_type=ScenarioType.LABOUR_UNREST,
        name="Arbeitskampf / Streik",
        description=(
            "Widespread strikes, union conflicts, or worker protests in "
            "key producing countries or sectors. Signals systemic suppression "
            "of labour rights. Based on ILO industrial action data."
        ),
        factors={
            _R.FREEDOM_OF_ASSOCIATION: 1.6,
            _R.COLLECTIVE_BARGAINING: 1.7,
            _R.WORKING_HOURS: 1.5,
            _R.MINIMUM_WAGE: 1.5,
            _R.OCCUPATIONAL_SAFETY: 1.4,
            _R.DISCRIMINATION: 1.3,
            _R.HUMAN_DIGNITY: 1.4,
            _R.FORCED_LABOUR: 1.3,
        },
        affected_nace_sections=["C", "H", "F", "G", "N"],
        sources=["ILO NORMLEX Database 2024", "ITUC Global Rights Index 2023"],
    ),

    ScenarioType.SUPPLY_SHORTAGE: ScenarioTemplate(
        scenario_type=ScenarioType.SUPPLY_SHORTAGE,
        name="Rohstoff- / Lieferengpass",
        description=(
            "Critical material shortage (semiconductor, rare earth, energy) "
            "drives sourcing from alternative, less-regulated suppliers. "
            "Increases risk of labour exploitation and environmental shortcuts."
        ),
        factors={
            _R.CHILD_LABOUR: 1.4,
            _R.FORCED_LABOUR: 1.5,
            _R.OCCUPATIONAL_SAFETY: 1.3,
            _R.ENVIRONMENTAL_DESTRUCTION: 1.4,
            _R.HARMFUL_CHEMICALS: 1.3,
            _R.COMMUNITY_RIGHTS: 1.3,
            _R.LAND_RIGHTS: 1.3,
            _R.MODERN_SLAVERY: 1.4,
            _R.MIGRANT_WORKER_RIGHTS: 1.3,
        },
        affected_nace_sections=["B", "C"],
        sources=["IEA Critical Minerals 2024", "OECD Supply Chain Resilience Report 2023"],
    ),
}


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------

class ScenarioSimulationEngine:
    """Deterministic scenario simulation over the CSDDD base risk matrix.

    No LLM, no randomness — pure arithmetic on static multiplier tables.
    M43 compliant: fully auditable, reproducible, explainable.
    """

    def simulate(
        self,
        nace_2digit: str,
        scenario_type: ScenarioType,
    ) -> SimulationResult:
        """Simulate a scenario for the given NACE sector.

        Args:
            nace_2digit: 2-digit NACE code, e.g. "29"
            scenario_type: which scenario to apply

        Returns:
            SimulationResult with baseline, scenario scores, deltas and explanations
        """
        code = nace_2digit.strip().zfill(2)
        template = _SCENARIO_TEMPLATES[scenario_type]
        baseline = get_scores(code)

        scenario_scores: dict[CSDDDRight, int] = {}
        delta: dict[CSDDDRight, int] = {}
        explanation: dict[CSDDDRight, str] = {}

        for right in CSDDDRight:
            base = baseline[right]
            factor = template.factors.get(right, 1.0)
            adjusted = min(10, max(1, round(base * factor)))
            scenario_scores[right] = adjusted
            delta[right] = adjusted - base

            if factor > 1.0:
                explanation[right] = (
                    f"Base {base}/10 × {factor:.1f} ({template.name}) = {adjusted}/10. "
                    f"Source: {template.sources[0]}."
                )
            else:
                explanation[right] = f"Unaffected by {template.name} (factor 1.0). Base: {base}/10."

        section_info = NACE_2DIGIT.get(code)
        sector_name = get_division_name(code)

        return SimulationResult(
            nace_2digit=code,
            sector_name=sector_name,
            scenario_type=scenario_type,
            scenario_name=template.name,
            baseline_scores=baseline,
            scenario_scores=scenario_scores,
            delta=delta,
            explanation=explanation,
            simulated_at=datetime.now(timezone.utc).isoformat(),
            calibration_version=CALIBRATION_VERSION,
        )

    def simulate_all_scenarios(
        self,
        nace_2digit: str,
    ) -> dict[ScenarioType, SimulationResult]:
        """Run all 6 scenarios for one sector in one call."""
        return {st: self.simulate(nace_2digit, st) for st in ScenarioType}

    def available_templates(self) -> list[ScenarioTemplate]:
        return list(_SCENARIO_TEMPLATES.values())

    def highest_risk_rights(
        self,
        result: SimulationResult,
        top_n: int = 5,
    ) -> list[tuple[CSDDDRight, int]]:
        """Return top-N CSDDD rights by scenario score, descending."""
        ranked = sorted(result.scenario_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_n]

    def rights_above_threshold(
        self,
        result: SimulationResult,
        threshold: int = 7,
    ) -> list[tuple[CSDDDRight, int]]:
        """Return all rights with scenario probability >= threshold."""
        return [
            (right, score)
            for right, score in result.scenario_scores.items()
            if score >= threshold
        ]
