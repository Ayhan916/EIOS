"""Gap Analyzer — CSDDD-015 (Art. 10 Abs. 2 lit. a).

Pure deterministic function — no LLM, no randomness.
Rule-based: each yes/no question with expected_answer="yes" where supplier
answered "no" → gap. Severity comes from question weight.

Traffic light per section:
  - any critical gap → RED
  - any high gap     → YELLOW
  - else             → GREEN

Overall: worst section traffic light.
"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.enums import GapSeverity, TrafficLight
from domain.supplier_assessment import AssessmentQuestion, AssessmentResponse, GapItem, GapReport, SectionScore

# Recommendations by (section, csddd_article) key — deterministic, config-driven
_RECOMMENDATIONS: dict[str, str] = {
    "company_structure": "Provide formal organizational chart and ownership structure documentation.",
    "hr_policies": "Adopt and publish a written Human Rights Due Diligence Policy referencing CSDDD Annex I.",
    "environment": "Implement documented environmental management procedures per CSDDD Annex II obligations.",
    "grievance": "Establish or participate in a grievance mechanism accessible to affected stakeholders (Art. 14).",
    "sub_suppliers": "Introduce cascade contractual clauses binding sub-suppliers to equivalent DD obligations (Art. 10 Abs. 2 lit. b).",
}

_WEIGHT_TO_SEVERITY: dict[int, str] = {
    5: GapSeverity.CRITICAL.value,
    4: GapSeverity.CRITICAL.value,
    3: GapSeverity.HIGH.value,
    2: GapSeverity.MEDIUM.value,
    1: GapSeverity.LOW.value,
}

_TRAFFIC_LIGHT_ORDER = [
    TrafficLight.GREEN.value,
    TrafficLight.YELLOW.value,
    TrafficLight.RED.value,
]


def _worst(lights: list[str]) -> str:
    if not lights:
        return TrafficLight.GREEN.value
    return max(lights, key=lambda x: _TRAFFIC_LIGHT_ORDER.index(x))


def analyze(
    questions: list[AssessmentQuestion],
    responses: list[AssessmentResponse],
    assessment_id: str,
    supplier_id: str,
) -> GapReport:
    """Compute gap report from answered questionnaire responses.

    Returns a GapReport with per-section traffic lights and a list of GapItems.
    Deterministic — same inputs always produce same output.
    """
    resp_map: dict[str, str] = {r.question_id: r.answer_value.strip().lower() for r in responses}

    gaps: list[GapItem] = []
    section_data: dict[str, dict] = {}

    for q in questions:
        if not q.is_active:
            continue
        sec = q.section
        if sec not in section_data:
            section_data[sec] = {"total": 0, "answered": 0, "gap_severities": []}
        section_data[sec]["total"] += 1

        answer = resp_map.get(q.id, "")
        if answer:
            section_data[sec]["answered"] += 1

        # Gap check: yes/no questions where supplier answered "no" for a required check
        if q.question_type == "yes_no" and q.is_required:
            expected = "yes"
            if answer in ("no", "0", "false", "nein"):
                severity = _WEIGHT_TO_SEVERITY.get(q.weight, GapSeverity.MEDIUM.value)
                section_data[sec]["gap_severities"].append(severity)
                recommendation = _RECOMMENDATIONS.get(sec, "Review CSDDD requirements and implement appropriate measures.")
                gaps.append(GapItem(
                    question_id=q.id,
                    section=sec,
                    csddd_article=q.csddd_article,
                    question_text=q.question_text,
                    answer_given=answer or "(no answer)",
                    expected_answer=expected,
                    severity=severity,
                    recommendation=recommendation,
                ))
        # Scale questions: score < 3 on 1-5 scale for required questions = gap
        elif q.question_type == "scale_1_5" and q.is_required and answer:
            try:
                score = int(answer)
                if score < 3:
                    severity = _WEIGHT_TO_SEVERITY.get(q.weight, GapSeverity.MEDIUM.value)
                    section_data[sec]["gap_severities"].append(severity)
                    recommendation = _RECOMMENDATIONS.get(sec, "Improve maturity level to at least 3/5.")
                    gaps.append(GapItem(
                        question_id=q.id,
                        section=sec,
                        csddd_article=q.csddd_article,
                        question_text=q.question_text,
                        answer_given=answer,
                        expected_answer="≥3",
                        severity=severity,
                        recommendation=recommendation,
                    ))
            except ValueError:
                pass

    section_scores: list[SectionScore] = []
    for sec, data in section_data.items():
        severities = data["gap_severities"]
        if any(s in (GapSeverity.CRITICAL.value,) for s in severities):
            tl = TrafficLight.RED.value
        elif any(s == GapSeverity.HIGH.value for s in severities):
            tl = TrafficLight.YELLOW.value
        elif severities:
            tl = TrafficLight.YELLOW.value
        else:
            tl = TrafficLight.GREEN.value
        section_scores.append(SectionScore(
            section=sec,
            total_questions=data["total"],
            answered=data["answered"],
            gaps=len(severities),
            traffic_light=tl,
        ))

    overall = _worst([s.traffic_light for s in section_scores])
    critical_count = sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL.value)

    return GapReport(
        assessment_id=assessment_id,
        supplier_id=supplier_id,
        section_scores=section_scores,
        gaps=gaps,
        overall_traffic_light=overall,
        total_gaps=len(gaps),
        critical_gaps=critical_count,
        generated_at=datetime.now(timezone.utc),
    )
