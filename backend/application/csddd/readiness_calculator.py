"""CSDDD Readiness Score Calculator — deterministic, auditable, no LLM.

Scoring per CSDDD article (140 total points, normalized to 100%):
  Art. 7  DD Policy & CoC           25 pt
  Art. 8  Scoping Study             20 pt
  Art. 10a Contractual Assurance    20 pt
  Art. 10b SME Support              10 pt
  Art. 11 CAP                       15 pt
  Art. 12 Remedy Cases              10 pt
  Art. 13 Stakeholder Engagement    15 pt
  Art. 15 Effectiveness Monitoring  15 pt
  Art. 16 Reporting                 10 pt
  ─────────────────────────────────
  Total                            140 pt

ReadinessLevel thresholds:
  FULLY_READY  = 100%
  READY        ≥  80%
  PARTIAL      ≥  40%
  NOT_READY    <  40%
"""
from __future__ import annotations

import json
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from domain.enums import ReadinessLevel
from domain.readiness import ArticleScore, ReadinessSnapshot

MAX_POINTS = 140


def _level(pct: float) -> str:
    if pct >= 100:
        return ReadinessLevel.FULLY_READY.value
    if pct >= 80:
        return ReadinessLevel.READY.value
    if pct >= 40:
        return ReadinessLevel.PARTIAL.value
    return ReadinessLevel.NOT_READY.value


def _pct(earned: int, maximum: int) -> float:
    return round((earned / maximum * 100) if maximum else 0, 1)


def _count(session: Session, table: str, where: str, params: dict) -> int:
    """Safe count — returns 0 if table/column does not exist yet."""
    try:
        row = session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), params).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


# ── Article scorers ───────────────────────────────────────────────────────────

def _score_art7(session: Session, org: str) -> ArticleScore:
    """Art. 7 — DD Policy & Code of Conduct (25 pt)."""
    gaps: list[str] = []
    earned = 0

    # Active approved policy (10 pt)
    approved_policies = _count(session, "dd_policies",
        "organization_id = :org AND policy_status = 'approved'", {"org": org})
    if approved_policies >= 1:
        earned += 10
    else:
        gaps.append("Keine genehmigte Due-Diligence-Policy (Art. 7 Abs. 1)")

    # Active code of conduct (10 pt)
    active_coc = _count(session, "codes_of_conduct",
        "organization_id = :org AND is_active = true", {"org": org})
    if active_coc >= 1:
        earned += 10
    else:
        gaps.append("Kein aktiver Code of Conduct (Art. 7 Abs. 2)")

    # CoC acceptances from suppliers (5 pt)
    coc_accepts = _count(session, "coc_acceptances",
        "organization_id = :org", {"org": org})
    if coc_accepts >= 3:
        earned += 5
    elif coc_accepts >= 1:
        earned += 2
        gaps.append("Wenige CoC-Akzeptanzen von Lieferanten (Art. 7 Abs. 2 lit. b)")
    else:
        gaps.append("Keine Lieferanten haben den CoC akzeptiert (Art. 7 Abs. 2 lit. b)")

    return ArticleScore(
        article="Art. 7",
        title="DD-Policy & Code of Conduct",
        earned_points=earned,
        max_points=25,
        score_pct=_pct(earned, 25),
        level=_level(_pct(earned, 25)),
        gaps=gaps,
    )


def _score_art8(session: Session, org: str) -> ArticleScore:
    """Art. 8 — Scoping Study (20 pt)."""
    gaps: list[str] = []
    earned = 0

    config_count = _count(session, "scoping_configs", "organization_id = :org", {"org": org})
    if config_count >= 1:
        earned += 5
    else:
        gaps.append("Kein Scoping-Konfiguration vorhanden (Art. 8 Abs. 3)")

    approved_study = _count(session, "scoping_studies",
        "organization_id = :org AND status = 'approved'", {"org": org})
    if approved_study >= 1:
        earned += 15
    else:
        any_study = _count(session, "scoping_studies", "organization_id = :org", {"org": org})
        if any_study >= 1:
            earned += 5
            gaps.append("Scoping Study vorhanden, aber noch nicht genehmigt (Art. 8 Abs. 3)")
        else:
            gaps.append("Keine Scoping Study durchgeführt (Art. 8 Abs. 3)")

    return ArticleScore(
        article="Art. 8",
        title="Scoping Study & Priorisierung",
        earned_points=earned,
        max_points=20,
        score_pct=_pct(earned, 20),
        level=_level(_pct(earned, 20)),
        gaps=gaps,
    )


def _score_art10a(session: Session, org: str) -> ArticleScore:
    """Art. 10a — Contractual Assurance (20 pt)."""
    gaps: list[str] = []
    earned = 0

    active_clauses = _count(session, "contract_clauses",
        "organization_id = :org AND is_active = true", {"org": org})
    if active_clauses >= 5:
        earned += 5
    elif active_clauses >= 1:
        earned += 2
        gaps.append(f"Nur {active_clauses} aktive Klauseln — mindestens 5 empfohlen (Art. 10 Abs. 2)")
    else:
        gaps.append("Keine Vertragsklauseln für Lieferanten definiert (Art. 10 Abs. 2)")

    total_assurances = _count(session, "contract_assurances",
        "organization_id = :org", {"org": org})
    accepted_assurances = _count(session, "contract_assurances",
        "organization_id = :org AND status = 'accepted'", {"org": org})

    if total_assurances > 0:
        accept_rate = accepted_assurances / total_assurances
        if accept_rate >= 0.8:
            earned += 10
        elif accept_rate >= 0.5:
            earned += 6
            gaps.append(f"Akzeptanzrate {round(accept_rate*100)}% — Ziel ≥80% (Art. 10 Abs. 4)")
        else:
            earned += 2
            gaps.append(f"Niedrige Akzeptanzrate {round(accept_rate*100)}% (Art. 10 Abs. 4)")
    else:
        gaps.append("Keine Zusicherungen erfasst (Art. 10 Abs. 2)")

    # Cascade confirmations (5 pt)
    cascade_needed = _count(session, "contract_clauses",
        "organization_id = :org AND cascade_required = true AND is_active = true", {"org": org})
    cascade_confirmed = _count(session, "contract_assurances",
        "organization_id = :org AND cascade_confirmed = true", {"org": org})
    if cascade_needed == 0 or cascade_confirmed >= cascade_needed:
        earned += 5
    elif cascade_confirmed > 0:
        earned += 2
        gaps.append(f"Cascade-Weitergabe unvollständig ({cascade_confirmed}/{cascade_needed}) (Art. 10 Abs. 3)")
    else:
        gaps.append("Keine Cascade-Weitergabe bestätigt (Art. 10 Abs. 3)")

    return ArticleScore(
        article="Art. 10a",
        title="Vertragliche Zusicherung",
        earned_points=earned,
        max_points=20,
        score_pct=_pct(earned, 20),
        level=_level(_pct(earned, 20)),
        gaps=gaps,
    )


def _score_art10b(session: Session, org: str) -> ArticleScore:
    """Art. 10b — SME Support (10 pt)."""
    gaps: list[str] = []
    earned = 0

    sme_profiles = _count(session, "sme_profiles",
        "organization_id = :org AND classification != 'large'", {"org": org})
    if sme_profiles >= 3:
        earned += 5
    elif sme_profiles >= 1:
        earned += 3
        gaps.append(f"Nur {sme_profiles} KMU-Lieferanten erfasst (Art. 10 Abs. 2 lit. b)")
    else:
        gaps.append("Keine KMU-Lieferanten klassifiziert (Art. 10 Abs. 2 lit. b)")

    active_programs = _count(session, "sme_support_programs",
        "organization_id = :org AND status IN ('active', 'completed')", {"org": org})
    if active_programs >= 1:
        earned += 5
    else:
        gaps.append("Keine Förderprogramme für KMU-Lieferanten (Art. 10 Abs. 2 lit. b)")

    return ArticleScore(
        article="Art. 10b",
        title="KMU-Unterstützung",
        earned_points=earned,
        max_points=10,
        score_pct=_pct(earned, 10),
        level=_level(_pct(earned, 10)),
        gaps=gaps,
    )


def _score_art11(session: Session, org: str) -> ArticleScore:
    """Art. 11 — Corrective Action Plans (15 pt)."""
    gaps: list[str] = []
    earned = 0

    total_caps = _count(session, "corrective_action_plans",
        "organization_id = :org", {"org": org})
    if total_caps == 0:
        gaps.append("Keine Korrekturmaßnahmen (CAPs) erfasst (Art. 11)")
        return ArticleScore(
            article="Art. 11",
            title="Corrective Action Plans",
            earned_points=0,
            max_points=15,
            score_pct=0.0,
            level=ReadinessLevel.NOT_READY.value,
            gaps=gaps,
        )

    earned += 5  # has CAPs

    closed_caps = _count(session, "corrective_action_plans",
        "organization_id = :org AND cap_status IN ('CLOSED', 'COMPLETED', 'Closed', 'Completed')",
        {"org": org})
    close_rate = closed_caps / total_caps
    if close_rate >= 0.8:
        earned += 10
    elif close_rate >= 0.5:
        earned += 6
        gaps.append(f"CAP-Abschlussrate {round(close_rate*100)}% — Ziel ≥80% (Art. 11)")
    else:
        earned += 2
        gaps.append(f"Niedrige CAP-Abschlussrate {round(close_rate*100)}% (Art. 11)")

    return ArticleScore(
        article="Art. 11",
        title="Corrective Action Plans",
        earned_points=earned,
        max_points=15,
        score_pct=_pct(earned, 15),
        level=_level(_pct(earned, 15)),
        gaps=gaps,
    )


def _score_art12(session: Session, org: str) -> ArticleScore:
    """Art. 12 — Remedy Cases (10 pt)."""
    gaps: list[str] = []
    earned = 0

    total = _count(session, "remedy_cases", "organization_id = :org", {"org": org})
    if total == 0:
        gaps.append("Keine Remedy Cases erfasst — Mechanismus nicht nachweisbar (Art. 12)")
        return ArticleScore(
            article="Art. 12",
            title="Remedy & Wiedergutmachung",
            earned_points=0,
            max_points=10,
            score_pct=0.0,
            level=ReadinessLevel.NOT_READY.value,
            gaps=gaps,
        )

    earned += 5
    closed = _count(session, "remedy_cases",
        "organization_id = :org AND status = 'closed'", {"org": org})
    close_rate = closed / total
    if close_rate >= 0.7:
        earned += 5
    elif close_rate >= 0.3:
        earned += 2
        gaps.append(f"Remedy-Abschlussrate {round(close_rate*100)}% — Ziel ≥70% (Art. 12)")
    else:
        gaps.append(f"Niedrige Remedy-Abschlussrate {round(close_rate*100)}% (Art. 12)")

    return ArticleScore(
        article="Art. 12",
        title="Remedy & Wiedergutmachung",
        earned_points=earned,
        max_points=10,
        score_pct=_pct(earned, 10),
        level=_level(_pct(earned, 10)),
        gaps=gaps,
    )


def _score_art13(session: Session, org: str) -> ArticleScore:
    """Art. 13 — Stakeholder Engagement (15 pt)."""
    gaps: list[str] = []
    earned = 0

    stakeholders = _count(session, "stakeholders",
        "organization_id = :org", {"org": org})
    if stakeholders >= 5:
        earned += 5
    elif stakeholders >= 1:
        earned += 3
        gaps.append(f"Nur {stakeholders} Stakeholder erfasst (Art. 13 Abs. 1)")
    else:
        gaps.append("Keine Stakeholder erfasst (Art. 13 Abs. 1)")

    consultations = _count(session, "stakeholder_consultations",
        "organization_id = :org", {"org": org})
    if consultations >= 3:
        earned += 10
    elif consultations >= 1:
        earned += 5
        gaps.append(f"Nur {consultations} Konsultationen — jährliche Durchführung empfohlen (Art. 13 Abs. 2)")
    else:
        gaps.append("Keine Stakeholder-Konsultationen dokumentiert (Art. 13 Abs. 2)")

    return ArticleScore(
        article="Art. 13",
        title="Stakeholder Engagement",
        earned_points=earned,
        max_points=15,
        score_pct=_pct(earned, 15),
        level=_level(_pct(earned, 15)),
        gaps=gaps,
    )


def _score_art15(session: Session, org: str) -> ArticleScore:
    """Art. 15 — Effectiveness Monitoring (15 pt)."""
    gaps: list[str] = []
    earned = 0

    indicators = _count(session, "effectiveness_indicators",
        "(organization_id = :org OR organization_id IS NULL)", {"org": org})
    if indicators >= 5:
        earned += 5
    elif indicators >= 1:
        earned += 2
        gaps.append(f"Nur {indicators} KPIs definiert (Art. 15 Abs. 1)")
    else:
        gaps.append("Keine Wirksamkeitsindikatoren definiert (Art. 15 Abs. 1)")

    reviews = _count(session, "effectiveness_reviews",
        "organization_id = :org", {"org": org})
    closed_reviews = _count(session, "effectiveness_reviews",
        "organization_id = :org AND status = 'closed'", {"org": org})

    if closed_reviews >= 1:
        earned += 10
    elif reviews >= 1:
        earned += 5
        gaps.append("Wirksamkeitsprüfung vorhanden aber nicht abgeschlossen (Art. 15 Abs. 2)")
    else:
        gaps.append("Keine Wirksamkeitsprüfungen durchgeführt (Art. 15 Abs. 2)")

    return ArticleScore(
        article="Art. 15",
        title="Wirksamkeits-Monitoring",
        earned_points=earned,
        max_points=15,
        score_pct=_pct(earned, 15),
        level=_level(_pct(earned, 15)),
        gaps=gaps,
    )


def _score_art16(session: Session, org: str) -> ArticleScore:
    """Art. 16 — Public Reporting (10 pt)."""
    gaps: list[str] = []
    earned = 0

    reports = _count(session, "reports",
        "(organization_id = :org OR organization_id IS NULL)", {"org": org})
    if reports >= 1:
        earned += 10
    else:
        gaps.append("Kein Nachhaltigkeitsbericht veröffentlicht (Art. 16 Abs. 1)")

    return ArticleScore(
        article="Art. 16",
        title="Öffentliche Berichterstattung",
        earned_points=earned,
        max_points=10,
        score_pct=_pct(earned, 10),
        level=_level(_pct(earned, 10)),
        gaps=gaps,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def compute(session: Session, organization_id: str, computed_by: str | None = None) -> ReadinessSnapshot:
    """Compute a CSDDD readiness snapshot for the given organization.

    Fully deterministic — no LLM. Results depend only on the DB state at call time.
    Suitable for audit trail and annual report export.
    """
    article_scores = [
        _score_art7(session, organization_id),
        _score_art8(session, organization_id),
        _score_art10a(session, organization_id),
        _score_art10b(session, organization_id),
        _score_art11(session, organization_id),
        _score_art12(session, organization_id),
        _score_art13(session, organization_id),
        _score_art15(session, organization_id),
        _score_art16(session, organization_id),
    ]

    total_earned = sum(a.earned_points for a in article_scores)
    overall_pct = round(total_earned / MAX_POINTS * 100, 1)

    return ReadinessSnapshot(
        id=str(uuid4()),
        organization_id=organization_id,
        overall_score_pct=overall_pct,
        overall_level=_level(overall_pct),
        article_scores=article_scores,
        computed_at=datetime.now(timezone.utc),
        computed_by=computed_by,
    )
