"""
CSDDD Sector Risk Register — Scenario Simulation Engine (TASK-003 Phase 5)

Applies predefined scenario multipliers to base matrix scores.
100% deterministic: same input → same output, always. No LLM at runtime (M43).

Usage:
    engine = ScenarioSimulationEngine()
    result = engine.simulate("29", ScenarioType.GEOPOLITICAL_CONFLICT)
"""

from __future__ import annotations

from datetime import UTC, datetime

from application.sector_intelligence.base_matrix import (
    CALIBRATION_VERSION,
    get_scores,
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

# ---------------------------------------------------------------------------
# Human-readable explanations per scenario × right (German, business language)
# Only defined for rights with factor > 1.0
# ---------------------------------------------------------------------------

_EXPLANATIONS: dict[ScenarioType, dict[CSDDDRight, str]] = {
    ScenarioType.GEOPOLITICAL_CONFLICT: {
        _R.FORCED_LABOUR: "In Konfliktgebieten werden Arbeitskräfte häufig unter Androhung von Gewalt zur Arbeit gezwungen. Staatliche Kontrollen brechen zusammen, Unternehmen verlieren den Überblick über ihre Lieferkette.",
        _R.MODERN_SLAVERY: "Krieg und Vertreibung machen Menschen besonders anfällig für Menschenhandel und moderne Sklaverei. Geflüchtete ohne Dokumente werden gezielt ausgebeutet.",
        _R.OCCUPATIONAL_SAFETY: "Zerstörte Infrastruktur, fehlende Schutzausrüstung und wegbrechende Behördenkontrollen machen sichere Arbeitsbedingungen in Konfliktregionen nahezu unmöglich.",
        _R.ENVIRONMENTAL_DESTRUCTION: "Militärische Operationen und zerstörte Industrieanlagen verursachen unkontrollierte Umweltschäden — Böden, Gewässer und Luft werden dauerhaft belastet.",
        _R.MIGRANT_WORKER_RIGHTS: "Migrantische Arbeitskräfte sind in Konflikten schutzlos: keine Dokumente, kein Zugang zu Botschaften, kein Rechtsschutz. Das Risiko schwerer Ausbeutung steigt stark.",
        _R.FREEDOM_OF_EXPRESSION: "In Kriegsgebieten werden Pressefreiheit und freie Meinungsäußerung systematisch unterdrückt, oft als 'Sicherheitsmaßnahme' gerechtfertigt.",
        _R.FREEDOM_OF_ASSOCIATION: "Gewerkschaften können in Konfliktgebieten nicht mehr frei operieren. Arbeitnehmerrechte werden oft per Notstandsgesetz ausgesetzt.",
        _R.COMMUNITY_RIGHTS: "Militäroperationen verdrängen Gemeinden von ihrem Land und zerstören traditionelle Lebensweisen — oft ohne jede Entschädigung.",
        _R.LAND_RIGHTS: "Zwangsvertreibungen, Besetzungen und die Vernichtung von Eigentumsbelegen untergraben Landrechte systematisch.",
        _R.HUMAN_DIGNITY: "Kriegsverbrechen, Folter und erniedrigende Behandlung von Zivilisten und Arbeitern sind in bewaffneten Konflikten dokumentierte Realität.",
        _R.WATER_RIGHTS: "Zerstörte Wasserinfrastruktur und strategische Blockaden gefährden den Zugang zu sauberem Wasser für Produktionsstandorte und Anwohner.",
    },
    ScenarioType.SANCTIONS_ESCALATION: {
        _R.FORCED_LABOUR: "Sanktionierter Druck zwingt Unternehmen, auf informelle Lieferketten auszuweichen — dort sind Arbeitnehmerrechte kaum kontrolliert und Zwangsarbeit verbreitet.",
        _R.MODERN_SLAVERY: "Wirtschaftssanktionen treiben Produktion in den Untergrund, wo Ausbeutung ohne staatliche Kontrolle möglich ist.",
        _R.MIGRANT_WORKER_RIGHTS: "Sanktionen erhöhen den Kostendruck — migrantische Arbeitskräfte werden als Puffer genutzt und besonders stark ausgebeutet.",
        _R.FREEDOM_OF_ASSOCIATION: "In sanktionierten Volkswirtschaften werden Gewerkschaftsrechte oft eingeschränkt, um die internationale Wettbewerbsfähigkeit zu erhalten.",
        _R.COLLECTIVE_BARGAINING: "Unter starkem wirtschaftlichem Druck durch Sanktionen werden Tarifverhandlungen ausgesetzt oder von Behörden blockiert.",
        _R.COMMUNITY_RIGHTS: "Sanktionierte Unternehmen umgehen Gemeinschaftskonsultationen, um Genehmigungsprozesse zu beschleunigen.",
    },
    ScenarioType.NATURAL_DISASTER: {
        _R.OCCUPATIONAL_SAFETY: "Katastrophen zerstören Sicherheitsinfrastruktur sofort — Schutzausrüstung fehlt, Notfallsysteme fallen aus, Arbeitnehmer sind erhöhten physischen Risiken ausgesetzt.",
        _R.ENVIRONMENTAL_DESTRUCTION: "Naturkatastrophen verursachen direkte, großflächige Umweltzerstörung. Dies ist der stärkste Faktor im Register (×2.0), da der Schaden nahezu unvermeidlich ist.",
        _R.WATER_RIGHTS: "Überschwemmungen kontaminieren Trinkwasser, Dürren verknappen es drastisch — der Zugang zu sauberem Wasser wird für Betriebe und Bevölkerung akut gefährdet.",
        _R.BIODIVERSITY: "Katastrophenereignisse zerstören Ökosysteme und Artenvielfalt großflächig und oft dauerhaft — Erholung dauert Jahrzehnte.",
        _R.COMMUNITY_RIGHTS: "Evakuierungen und Katastrophennothilfe verdrängen Gemeinden oft dauerhaft von ihrem Land, ohne adäquate Entschädigung.",
        _R.LAND_RIGHTS: "Überschwemmungen, Erdrutsche und Brände vernichten Grundstücke und Eigentumsbelege — Rückkehr und Wiederaufbau werden rechtlich unmöglich.",
        _R.FORCED_LABOUR: "In der Katastrophennachsorge und beim Wiederaufbau werden Arbeitskräfte oft unter Druck und ohne faire Vergütung eingesetzt.",
        _R.MIGRANT_WORKER_RIGHTS: "Katastrophengebiete ziehen migrantische Arbeitsmigration für den Wiederaufbau an — häufig ohne arbeitsrechtlichen Schutz.",
        _R.HARMFUL_CHEMICALS: "Zerstörte Industrieanlagen und Lager setzen Chemikalien unkontrolliert frei — in Boden, Wasser und Luft.",
        _R.HAZARDOUS_WASTE: "Beschädigte Deponien und Lagerstätten lassen gefährliche Abfälle in die Umwelt gelangen, oft ohne dass es zeitnah bemerkt wird.",
    },
    ScenarioType.REGULATORY_CHANGE: {
        _R.CHILD_LABOUR: "CSDDD und LkSG erzwingen tiefere Lieferkettenprüfungen — bisher verborgene Kinderarbeit bei Unterlieferanten wird jetzt erstmals sichtbar.",
        _R.FORCED_LABOUR: "Neue Sorgfaltspflichtgesetze verlangen Nachweise auf tieferen Lieferkettenstufen, wo Zwangsarbeit bisher nicht geprüft wurde.",
        _R.OCCUPATIONAL_SAFETY: "Erweiterte Berichtspflichten legen Sicherheitsmängel offen, die nach bisherigem Recht nicht meldepflichtig waren.",
        _R.ENVIRONMENTAL_DESTRUCTION: "CSDDD Annex I verpflichtet erstmals explizit zur Umweltprüfung in der Lieferkette — latente Risiken werden durch neue Audits sichtbar.",
        _R.HARMFUL_CHEMICALS: "Neue Chemikalienvorschriften in CSDDD und REACH-Erweiterungen erfassen bisher ungemeldete Substanzen.",
        _R.HAZARDOUS_WASTE: "Verschärfte Abfallvorschriften erhöhen den Prüfaufwand erheblich und decken bestehende Verstöße bei Lieferanten auf.",
        _R.BIODIVERSITY: "CSRD-Biodiversitätsberichtspflichten sind neu — bisherige Aktivitäten wurden nie systematisch auf Naturverträglichkeit geprüft.",
        _R.DISCRIMINATION: "Erweiterte ESG-Berichtsstandards schließen nun Diskriminierungsdaten (Lohngleichheit, Diversität) verpflichtend ein.",
        _R.FREEDOM_OF_ASSOCIATION: "Neue Due-Diligence-Anforderungen umfassen erstmals systematische Prüfungen der Gewerkschaftsfreiheit bei Lieferanten.",
    },
    ScenarioType.LABOUR_UNREST: {
        _R.FREEDOM_OF_ASSOCIATION: "Streiks und Arbeitskämpfe sind das deutlichste Signal dafür, dass Gewerkschaftsrechte unterdrückt werden oder es in Kürze sein werden.",
        _R.COLLECTIVE_BARGAINING: "Arbeitskämpfe entstehen fast immer, weil Tarifverhandlungen scheitern oder vom Arbeitgeber verweigert werden — direkter Kausalzusammenhang.",
        _R.WORKING_HOURS: "Übermäßige Arbeitszeiten ohne Ausgleich sind weltweit einer der häufigsten Auslöser für Streiks und Arbeitsniederlegungen.",
        _R.MINIMUM_WAGE: "Lohnstreitigkeiten sind der häufigste Grund für Arbeitskampfmaßnahmen in Schwellen- und Entwicklungsländern.",
        _R.OCCUPATIONAL_SAFETY: "Unsichere Arbeitsbedingungen ohne Verbesserung trotz Beschwerden sind ein zentraler Streikauslöser in Produktionsbetrieben.",
        _R.DISCRIMINATION: "Arbeitskonflikte offenbaren oft tiefer liegende Diskriminierungsprobleme — z.B. nach Geschlecht, Herkunft oder Gewerkschaftsmitgliedschaft.",
        _R.HUMAN_DIGNITY: "Erniedrigende Behandlung am Arbeitsplatz (Demütigungen, Schikanierung) ist ein dokumentierter Konflikttreiber in der Industrie.",
        _R.FORCED_LABOUR: "In Regionen mit aktiven Arbeitskämpfen reagieren manche Arbeitgeber mit Einschüchterung oder Zwang — das Risiko eskaliert.",
    },
    ScenarioType.SUPPLY_SHORTAGE: {
        _R.CHILD_LABOUR: "Engpässe zwingen Einkäufer zu Notlieferanten in wenig regulierten Regionen, wo Kinderarbeit nicht kontrolliert wird.",
        _R.FORCED_LABOUR: "Extremer Preisdruck durch Materialknappheit fördert Ausbeutung in alternativen, unkontrollierten Lieferketten.",
        _R.OCCUPATIONAL_SAFETY: "Beschleunigter Abbau und Produktion unter Zeitdruck erhöhen Unfallrisiken — Sicherheitsstandards werden für Schnelligkeit geopfert.",
        _R.ENVIRONMENTAL_DESTRUCTION: "Rohstoffknappheit treibt den Abbau in ökologisch sensible Gebiete ohne Schutzauflagen und Umweltverträglichkeitsprüfungen.",
        _R.HARMFUL_CHEMICALS: "Alternativlieferanten für kritische Materialien verwenden oft nicht zertifizierte Prozesschemikalien, da reguläre Quellen fehlen.",
        _R.COMMUNITY_RIGHTS: "Eilprojekte zur Rohstoffbeschaffung umgehen Gemeinschaftskonsultationen, die gesetzlich oder nach FPIC-Standard erforderlich wären.",
        _R.LAND_RIGHTS: "Notabbau in neuen Gebieten ignoriert häufig bestehende Landrechte indigener und lokaler Gemeinschaften.",
        _R.MODERN_SLAVERY: "Hochpreisphasen für kritische Materialien (Kobalt, Lithium) korrelieren mit dokumentierten Sklaverei-Vorfällen in Minen.",
        _R.MIGRANT_WORKER_RIGHTS: "Engpässe erhöhen die Nachfrage nach billigen migrantischen Arbeitskräften in der Extraktion — ohne ausreichenden Rechtsschutz.",
    },
}


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
                custom = _EXPLANATIONS.get(scenario_type, {}).get(right)
                explanation[right] = (
                    custom
                    if custom
                    else (
                        f"Erhoeht um Faktor {factor:.1f} unter Szenario '{template.name}'. "
                        f"Baseline: {base}/10, Szenario: {adjusted}/10. Quelle: {template.sources[0]}."
                    )
                )
            else:
                explanation[right] = (
                    f"Dieses Recht ist von Szenario '{template.name}' nicht direkt betroffen. "
                    f"Baseline-Wert {base}/10 bleibt unveraendert."
                )

        NACE_2DIGIT.get(code)
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
            simulated_at=datetime.now(UTC).isoformat(),
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
            (right, score) for right, score in result.scenario_scores.items() if score >= threshold
        ]
