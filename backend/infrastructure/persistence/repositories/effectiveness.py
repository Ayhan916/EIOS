"""Repositories for Effectiveness Monitoring (CSDDD Art. 15)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from domain.effectiveness import (
    CAPEffectivenessSnapshot,
    EffectivenessIndicator,
    EffectivenessReview,
    ReviewLine,
)
from domain.enums import EffectivenessReviewStatus as ReviewStatus
from infrastructure.persistence.models.corrective_action_plan import CorrectiveActionPlanModel
from infrastructure.persistence.models.effectiveness import (
    EffectivenessIndicatorModel,
    EffectivenessReviewModel,
    ReviewLineModel,
)


def _ind_to_domain(m: EffectivenessIndicatorModel) -> EffectivenessIndicator:
    return EffectivenessIndicator(
        id=m.id,
        organization_id=m.organization_id,
        name=m.name,
        description=m.description or "",
        indicator_type=m.indicator_type,
        unit=m.unit,
        data_source=m.data_source,
        csddd_article=m.csddd_article,
        risk_category=m.risk_category,
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _line_to_domain(m: ReviewLineModel) -> ReviewLine:
    return ReviewLine(
        id=m.id,
        review_id=m.review_id,
        indicator_id=m.indicator_id,
        indicator_name=m.indicator_name,
        measured_value=m.measured_value,
        measured_text=m.measured_text,
        comment=m.comment,
        auto_populated=m.auto_populated,
    )


def _review_to_domain(m: EffectivenessReviewModel, lines: list[ReviewLine]) -> EffectivenessReview:
    return EffectivenessReview(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        period_start=m.period_start,
        period_end=m.period_end,
        overall_rating=m.overall_rating,
        key_findings=m.key_findings,
        improvement_actions=m.improvement_actions,
        status=m.status,
        submitted_at=m.submitted_at,
        submitted_by=m.submitted_by,
        approved_at=m.approved_at,
        approved_by=m.approved_by,
        lines=lines,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── Seeds ─────────────────────────────────────────────────────────────────────

SEED_INDICATORS = [
    # Quantitative — automatic
    (
        "Closed CAPs (12M)",
        "Number of corrective action plans closed in the last 12 months",
        "quantitative",
        "count",
        "automatic",
        "Art. 11",
        "corrective_actions",
    ),
    (
        "Overdue CAPs",
        "Number of CAPs past their deadline",
        "quantitative",
        "count",
        "automatic",
        "Art. 11",
        "corrective_actions",
    ),
    (
        "Grievance Response Time (Ø)",
        "Average days to first response on grievance cases",
        "quantitative",
        "days",
        "automatic",
        "Art. 14",
        "grievance",
    ),
    (
        "Grievance Remediation Rate",
        "Percentage of grievances leading to a remedy case",
        "quantitative",
        "percent",
        "automatic",
        "Art. 12",
        "grievance",
    ),
    (
        "Remedy Cases Closed (12M)",
        "Number of remedy cases closed in the last 12 months",
        "quantitative",
        "count",
        "automatic",
        "Art. 12",
        "remedy",
    ),
    (
        "Stakeholder Consultations (12M)",
        "Number of formal stakeholder consultations conducted",
        "quantitative",
        "count",
        "automatic",
        "Art. 13",
        "stakeholder",
    ),
    (
        "High-Risk Suppliers (%)",
        "Share of suppliers rated high-risk in current assessments",
        "quantitative",
        "percent",
        "automatic",
        "Art. 8",
        "risk",
    ),
    (
        "Audit Coverage (%)",
        "Percentage of tier-1 suppliers assessed in the last 12 months",
        "quantitative",
        "percent",
        "automatic",
        "Art. 8",
        "audit",
    ),
    (
        "Average Risk Score Δ (CAPs)",
        "Mean risk score reduction after CAP closure",
        "quantitative",
        "score",
        "automatic",
        "Art. 15",
        "risk",
    ),
    # Quantitative — manual
    (
        "Policy Awareness Rate",
        "Percentage of employees aware of the DD policy",
        "quantitative",
        "percent",
        "manual",
        "Art. 7",
        "governance",
    ),
    (
        "CoC Acceptance Rate (%)",
        "Percentage of suppliers who have accepted the Code of Conduct",
        "quantitative",
        "percent",
        "manual",
        "Art. 7",
        "governance",
    ),
    (
        "Training Completion Rate (%)",
        "Percentage of relevant staff completing DD training",
        "quantitative",
        "percent",
        "manual",
        "Art. 7",
        "human_rights",
    ),
    (
        "Incident Recurrence Rate (%)",
        "Percentage of closed findings that recurred within 24 months",
        "quantitative",
        "percent",
        "manual",
        "Art. 15",
        "risk",
    ),
    # Qualitative — manual
    (
        "Stakeholder Satisfaction",
        "Overall satisfaction of stakeholders with DD engagement process",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 13",
        "stakeholder",
    ),
    (
        "Audit Finding Trend",
        "Directional assessment of findings trend vs. prior period",
        "qualitative",
        "improving/stable/worsening",
        "manual",
        "Art. 8",
        "audit",
    ),
    (
        "Management Commitment",
        "Assessment of board-level commitment to DD implementation",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 22",
        "governance",
    ),
    (
        "Process Maturity",
        "Maturity level of DD processes across the organisation",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 15",
        "governance",
    ),
    (
        "Supplier Collaboration Quality",
        "Quality of supplier engagement in DD activities",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 10",
        "supplier",
    ),
    (
        "Grievance Mechanism Accessibility",
        "Effectiveness of the grievance mechanism for affected parties",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 14",
        "grievance",
    ),
    (
        "Policy Effectiveness Assessment",
        "Expert assessment of whether DD policy achieves stated objectives",
        "qualitative",
        "1-5 scale",
        "manual",
        "Art. 7",
        "governance",
    ),
]


class SQLEffectivenessIndicatorRepository:
    def __init__(self, db: Session):
        self.db = db

    def seed_if_empty(self) -> None:
        count = (
            self.db.query(EffectivenessIndicatorModel)
            .filter(EffectivenessIndicatorModel.organization_id.is_(None))
            .count()
        )
        if count > 0:
            return
        for name, desc, ind_type, unit, source, article, risk_cat in SEED_INDICATORS:
            self.db.add(
                EffectivenessIndicatorModel(
                    id=uuid4(),
                    organization_id=None,
                    name=name,
                    description=desc,
                    indicator_type=ind_type,
                    unit=unit,
                    data_source=source,
                    csddd_article=article,
                    risk_category=risk_cat,
                    is_active=True,
                )
            )
        self.db.flush()

    def list(self, org_id: UUID, risk_category: str | None = None) -> list[EffectivenessIndicator]:
        q = (
            self.db.query(EffectivenessIndicatorModel)
            .filter(
                (EffectivenessIndicatorModel.organization_id.is_(None))
                | (EffectivenessIndicatorModel.organization_id == org_id)
            )
            .filter(EffectivenessIndicatorModel.is_active)
        )
        if risk_category:
            q = q.filter(EffectivenessIndicatorModel.risk_category == risk_category)
        return [_ind_to_domain(m) for m in q.order_by(EffectivenessIndicatorModel.name).all()]

    def get(self, indicator_id: UUID) -> EffectivenessIndicator | None:
        m = (
            self.db.query(EffectivenessIndicatorModel)
            .filter(EffectivenessIndicatorModel.id == indicator_id)
            .first()
        )
        return _ind_to_domain(m) if m else None

    def create(self, org_id: UUID, data: dict) -> EffectivenessIndicator:
        m = EffectivenessIndicatorModel(
            id=uuid4(),
            organization_id=org_id,
            name=data["name"],
            description=data.get("description"),
            indicator_type=data.get("indicator_type", "qualitative"),
            unit=data.get("unit", ""),
            data_source=data.get("data_source", "manual"),
            csddd_article=data.get("csddd_article", ""),
            risk_category=data.get("risk_category"),
            is_active=True,
        )
        self.db.add(m)
        self.db.flush()
        return _ind_to_domain(m)


class SQLEffectivenessReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, org_id: UUID, data: dict) -> EffectivenessReview:
        m = EffectivenessReviewModel(
            id=uuid4(),
            organization_id=org_id,
            title=data["title"],
            period_start=data["period_start"],
            period_end=data["period_end"],
            overall_rating=data.get("overall_rating"),
            key_findings=data.get("key_findings"),
            improvement_actions=data.get("improvement_actions"),
            status=ReviewStatus.DRAFT.value,
        )
        self.db.add(m)
        self.db.flush()
        return _review_to_domain(m, [])

    def get(self, review_id: UUID, org_id: UUID) -> EffectivenessReview | None:
        m = (
            self.db.query(EffectivenessReviewModel)
            .filter(
                EffectivenessReviewModel.id == review_id,
                EffectivenessReviewModel.organization_id == org_id,
            )
            .first()
        )
        if not m:
            return None
        lines = [
            _line_to_domain(l)
            for l in self.db.query(ReviewLineModel)
            .filter(ReviewLineModel.review_id == review_id)
            .all()
        ]
        return _review_to_domain(m, lines)

    def list_by_org(
        self, org_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[EffectivenessReview]:
        rows = (
            self.db.query(EffectivenessReviewModel)
            .filter(EffectivenessReviewModel.organization_id == org_id)
            .order_by(EffectivenessReviewModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        result = []
        for m in rows:
            lines = [
                _line_to_domain(l)
                for l in self.db.query(ReviewLineModel)
                .filter(ReviewLineModel.review_id == m.id)
                .all()
            ]
            result.append(_review_to_domain(m, lines))
        return result

    def update(self, review_id: UUID, org_id: UUID, data: dict) -> EffectivenessReview | None:
        m = (
            self.db.query(EffectivenessReviewModel)
            .filter(
                EffectivenessReviewModel.id == review_id,
                EffectivenessReviewModel.organization_id == org_id,
            )
            .first()
        )
        if not m:
            return None
        for k, v in data.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self.db.flush()
        lines = [
            _line_to_domain(l)
            for l in self.db.query(ReviewLineModel)
            .filter(ReviewLineModel.review_id == review_id)
            .all()
        ]
        return _review_to_domain(m, lines)

    def submit(
        self, review_id: UUID, org_id: UUID, submitted_by: str
    ) -> EffectivenessReview | None:
        m = (
            self.db.query(EffectivenessReviewModel)
            .filter(
                EffectivenessReviewModel.id == review_id,
                EffectivenessReviewModel.organization_id == org_id,
            )
            .first()
        )
        if not m:
            return None
        m.status = ReviewStatus.SUBMITTED.value
        m.submitted_at = datetime.now(UTC)
        m.submitted_by = submitted_by
        self.db.flush()
        lines = [
            _line_to_domain(l)
            for l in self.db.query(ReviewLineModel)
            .filter(ReviewLineModel.review_id == review_id)
            .all()
        ]
        return _review_to_domain(m, lines)

    def close(self, review_id: UUID, org_id: UUID, approved_by: str) -> EffectivenessReview | None:
        """HUMAN MANAGER/ADMIN ONLY — AI agents MUST NOT call this."""
        m = (
            self.db.query(EffectivenessReviewModel)
            .filter(
                EffectivenessReviewModel.id == review_id,
                EffectivenessReviewModel.organization_id == org_id,
            )
            .first()
        )
        if not m:
            return None
        m.status = ReviewStatus.CLOSED.value
        m.approved_at = datetime.now(UTC)
        m.approved_by = approved_by
        self.db.flush()
        lines = [
            _line_to_domain(l)
            for l in self.db.query(ReviewLineModel)
            .filter(ReviewLineModel.review_id == review_id)
            .all()
        ]
        return _review_to_domain(m, lines)

    def upsert_line(self, review_id: UUID, data: dict) -> ReviewLine:
        existing = (
            self.db.query(ReviewLineModel)
            .filter(
                ReviewLineModel.review_id == review_id,
                ReviewLineModel.indicator_id == data["indicator_id"],
            )
            .first()
        )
        if existing:
            existing.measured_value = data.get("measured_value")
            existing.measured_text = data.get("measured_text")
            existing.comment = data.get("comment")
            self.db.flush()
            return _line_to_domain(existing)
        m = ReviewLineModel(
            id=uuid4(),
            review_id=review_id,
            indicator_id=data["indicator_id"],
            indicator_name=data.get("indicator_name", ""),
            measured_value=data.get("measured_value"),
            measured_text=data.get("measured_text"),
            comment=data.get("comment"),
            auto_populated=data.get("auto_populated", False),
        )
        self.db.add(m)
        self.db.flush()
        return _line_to_domain(m)


class SQLCAPSnapshotRepository:
    """Read/write baseline and closed risk-score snapshots on CAP rows."""

    def __init__(self, db: Session):
        self.db = db

    def get_snapshot(self, cap_id: str, org_id: UUID) -> CAPEffectivenessSnapshot | None:
        m = (
            self.db.query(CorrectiveActionPlanModel)
            .filter(
                CorrectiveActionPlanModel.id == cap_id,
                CorrectiveActionPlanModel.organization_id == str(org_id),
            )
            .first()
        )
        if not m:
            return None
        baseline = getattr(m, "baseline_score", None)
        closed = getattr(m, "closed_score", None)
        return CAPEffectivenessSnapshot(
            cap_id=cap_id,
            organization_id=org_id,
            baseline_score=baseline,
            closed_score=closed,
            risk_delta=round(closed - baseline, 2)
            if (baseline is not None and closed is not None)
            else None,
            snapshot_taken_at=getattr(m, "closed_at", None),
        )

    def set_baseline(self, cap_id: str, org_id: UUID, score: float) -> None:
        m = (
            self.db.query(CorrectiveActionPlanModel)
            .filter(
                CorrectiveActionPlanModel.id == cap_id,
                CorrectiveActionPlanModel.organization_id == str(org_id),
            )
            .first()
        )
        if m:
            m.baseline_score = score
            self.db.flush()

    def set_closed_score(self, cap_id: str, org_id: UUID, score: float) -> None:
        m = (
            self.db.query(CorrectiveActionPlanModel)
            .filter(
                CorrectiveActionPlanModel.id == cap_id,
                CorrectiveActionPlanModel.organization_id == str(org_id),
            )
            .first()
        )
        if m:
            m.closed_score = score
            self.db.flush()


class SQLEffectivenessDashboardRepository:
    """Aggregates all 6 core metrics for the live monitoring dashboard."""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard(self, org_id: UUID) -> dict:
        from datetime import timedelta

        from infrastructure.persistence.models.corrective_action_plan import (
            CorrectiveActionPlanModel,
        )

        now = datetime.now(UTC)
        twelve_months_ago = now - timedelta(days=365)

        # CAP metrics
        all_caps = (
            self.db.query(CorrectiveActionPlanModel)
            .filter(CorrectiveActionPlanModel.organization_id == str(org_id))
            .all()
        )
        open_caps = sum(1 for c in all_caps if c.cap_status not in ("CLOSED", "VERIFIED"))
        overdue_caps = sum(
            1
            for c in all_caps
            if c.cap_status not in ("CLOSED", "VERIFIED")
            and c.deadline is not None
            and c.deadline < now.date()
        )
        closed_caps_12m = sum(
            1
            for c in all_caps
            if c.cap_status in ("CLOSED", "VERIFIED")
            and c.closed_at is not None
            and c.closed_at >= twelve_months_ago
        )

        # Risk score delta from CAP snapshots
        snapped = [
            c
            for c in all_caps
            if getattr(c, "baseline_score", None) is not None
            and getattr(c, "closed_score", None) is not None
        ]
        avg_risk_delta = (
            round(sum(c.closed_score - c.baseline_score for c in snapped) / len(snapped), 2)
            if snapped
            else None
        )

        # Try stakeholder consultations
        try:
            from infrastructure.persistence.models.stakeholder import StakeholderConsultationModel

            consultations_12m = (
                self.db.query(StakeholderConsultationModel)
                .filter(
                    StakeholderConsultationModel.organization_id == org_id,
                    StakeholderConsultationModel.scheduled_date >= twelve_months_ago,
                )
                .count()
            )
        except Exception:
            consultations_12m = 0

        # Try remedy cases for grievance response time
        try:
            from infrastructure.persistence.models.remedy_case import RemedyCaseModel

            remedy_count_12m = (
                self.db.query(RemedyCaseModel)
                .filter(
                    RemedyCaseModel.organization_id == org_id,
                    RemedyCaseModel.created_at >= twelve_months_ago,
                    RemedyCaseModel.status.in_(["completed", "verified"]),
                )
                .count()
            )
        except Exception:
            remedy_count_12m = 0

        return {
            "open_caps": open_caps,
            "overdue_caps": overdue_caps,
            "closed_caps_12m": closed_caps_12m,
            "avg_risk_delta": avg_risk_delta,
            "stakeholder_consultations_12m": consultations_12m,
            "remedy_cases_closed_12m": remedy_count_12m,
            "escalation_needed": overdue_caps > 5
            or (avg_risk_delta is not None and avg_risk_delta > 1.0),
            "generated_at": now.isoformat(),
        }
