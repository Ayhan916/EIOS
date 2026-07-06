"""Repository — Impact Severity Assessments (CSDDD Art. 3/6)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from application.csddd.severity_calculator import assess
from domain.enums import ImpactType, SeverityLevel
from domain.impact_assessment import ImpactAssessment
from infrastructure.persistence.models.impact_assessment import ImpactAssessmentModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_domain(m: ImpactAssessmentModel) -> ImpactAssessment:
    return ImpactAssessment(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        impact_type=m.impact_type,
        entity_type=m.entity_type,
        entity_id=m.entity_id,
        gravity=m.gravity,
        scope=m.scope,
        remediability=m.remediability,
        likelihood=m.likelihood,
        severity_score=m.severity_score,
        priority_score=m.priority_score,
        severity_level=m.severity_level,
        justification=m.justification,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLImpactAssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(
        self,
        organization_id: str,
        severity_level: str | None = None,
        impact_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[ImpactAssessment]:
        stmt = select(ImpactAssessmentModel).where(
            ImpactAssessmentModel.organization_id == organization_id
        )
        if severity_level:
            stmt = stmt.where(ImpactAssessmentModel.severity_level == severity_level)
        if impact_type:
            stmt = stmt.where(ImpactAssessmentModel.impact_type == impact_type)
        if entity_id:
            stmt = stmt.where(ImpactAssessmentModel.entity_id == entity_id)
        stmt = stmt.order_by(ImpactAssessmentModel.priority_score.desc())
        return [_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, assessment_id: str, organization_id: str) -> ImpactAssessment | None:
        m = self._s.get(ImpactAssessmentModel, assessment_id)
        if not m or m.organization_id != organization_id:
            return None
        return _to_domain(m)

    def create(
        self,
        organization_id: str,
        title: str,
        impact_type: str,
        entity_type: str,
        entity_id: str | None,
        gravity: int,
        scope: int,
        remediability: int,
        likelihood: int,
        justification: str | None,
        created_by: str,
    ) -> ImpactAssessment:
        scores = assess(gravity, scope, remediability, likelihood)
        m = ImpactAssessmentModel(
            id=str(uuid4()),
            organization_id=organization_id,
            title=title,
            impact_type=impact_type,
            entity_type=entity_type,
            entity_id=entity_id,
            gravity=gravity,
            scope=scope,
            remediability=remediability,
            likelihood=likelihood,
            severity_score=scores["severity_score"],
            priority_score=scores["priority_score"],
            severity_level=scores["severity_level"],
            justification=justification,
            created_by=created_by,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _to_domain(m)

    def update(
        self,
        assessment_id: str,
        organization_id: str,
        gravity: int,
        scope: int,
        remediability: int,
        likelihood: int,
        title: str | None = None,
        justification: str | None = None,
    ) -> ImpactAssessment | None:
        m = self._s.get(ImpactAssessmentModel, assessment_id)
        if not m or m.organization_id != organization_id:
            return None
        scores = assess(gravity, scope, remediability, likelihood)
        m.gravity = gravity
        m.scope = scope
        m.remediability = remediability
        m.likelihood = likelihood
        m.severity_score = scores["severity_score"]
        m.priority_score = scores["priority_score"]
        m.severity_level = scores["severity_level"]
        if title:
            m.title = title
        if justification is not None:
            m.justification = justification
        m.updated_at = _now()
        self._s.flush()
        return _to_domain(m)

    def delete(self, assessment_id: str, organization_id: str) -> bool:
        m = self._s.get(ImpactAssessmentModel, assessment_id)
        if not m or m.organization_id != organization_id:
            return False
        self._s.delete(m)
        self._s.flush()
        return True

    def dashboard(self, organization_id: str) -> dict:
        all_a = self.list_org(organization_id)
        total = len(all_a)
        by_level = {lvl.value: 0 for lvl in SeverityLevel}
        by_type = {t.value: 0 for t in ImpactType}
        for a in all_a:
            by_level[a.severity_level] = by_level.get(a.severity_level, 0) + 1
            by_type[a.impact_type] = by_type.get(a.impact_type, 0) + 1
        top5 = all_a[:5]
        avg_severity = round(sum(a.severity_score for a in all_a) / total, 2) if total else 0.0
        return {
            "total": total,
            "critical": by_level.get(SeverityLevel.CRITICAL.value, 0),
            "high": by_level.get(SeverityLevel.HIGH.value, 0),
            "medium": by_level.get(SeverityLevel.MEDIUM.value, 0),
            "low": by_level.get(SeverityLevel.LOW.value, 0),
            "avg_severity_score": avg_severity,
            "by_type": by_type,
            "top5_priority": [
                {
                    "id": a.id,
                    "title": a.title,
                    "severity_score": a.severity_score,
                    "priority_score": a.priority_score,
                    "severity_level": a.severity_level,
                    "impact_type": a.impact_type,
                }
                for a in top5
            ],
        }

    def preview(
        self, gravity: int, scope: int, remediability: int, likelihood: int
    ) -> dict:
        """Preview score without persisting — for live calculator UI."""
        return assess(gravity, scope, remediability, likelihood)
