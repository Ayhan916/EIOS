"""Repository — CSDDD Readiness Snapshots (CSDDD-011)."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.readiness import ArticleScore, ReadinessSnapshot
from infrastructure.persistence.models.readiness import ReadinessSnapshotModel


def _snapshot_to_domain(m: ReadinessSnapshotModel) -> ReadinessSnapshot:
    raw = json.loads(m.article_scores_json)
    article_scores = [
        ArticleScore(
            article=a["article"],
            title=a["title"],
            earned_points=a["earned_points"],
            max_points=a["max_points"],
            score_pct=a["score_pct"],
            level=a["level"],
            gaps=a["gaps"],
        )
        for a in raw
    ]
    return ReadinessSnapshot(
        id=m.id,
        organization_id=m.organization_id,
        overall_score_pct=m.overall_score_pct,
        overall_level=m.overall_level,
        article_scores=article_scores,
        computed_at=m.computed_at,
        computed_by=m.computed_by,
    )


class SQLReadinessRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def save(self, snapshot: ReadinessSnapshot) -> ReadinessSnapshot:
        article_scores_json = json.dumps([
            {
                "article": a.article,
                "title": a.title,
                "earned_points": a.earned_points,
                "max_points": a.max_points,
                "score_pct": a.score_pct,
                "level": a.level,
                "gaps": a.gaps,
            }
            for a in snapshot.article_scores
        ])
        m = ReadinessSnapshotModel(
            id=snapshot.id,
            organization_id=snapshot.organization_id,
            overall_score_pct=snapshot.overall_score_pct,
            overall_level=snapshot.overall_level,
            article_scores_json=article_scores_json,
            computed_at=snapshot.computed_at,
            computed_by=snapshot.computed_by,
        )
        self._s.add(m)
        self._s.flush()
        return snapshot

    def latest(self, organization_id: str) -> ReadinessSnapshot | None:
        stmt = (
            select(ReadinessSnapshotModel)
            .where(ReadinessSnapshotModel.organization_id == organization_id)
            .order_by(ReadinessSnapshotModel.computed_at.desc())
            .limit(1)
        )
        m = self._s.execute(stmt).scalar_one_or_none()
        return _snapshot_to_domain(m) if m else None

    def history(self, organization_id: str, limit: int = 12) -> list[ReadinessSnapshot]:
        stmt = (
            select(ReadinessSnapshotModel)
            .where(ReadinessSnapshotModel.organization_id == organization_id)
            .order_by(ReadinessSnapshotModel.computed_at.desc())
            .limit(limit)
        )
        return [_snapshot_to_domain(m) for m in self._s.execute(stmt).scalars().all()]
