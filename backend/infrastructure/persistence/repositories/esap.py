"""Repository — ESAP Submissions (CSDDD-009)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.enums import ESAPSubmissionStatus
from domain.esap import ESAPSubmission
from infrastructure.persistence.models.esap import ESAPSubmissionModel


def _now() -> datetime:
    return datetime.now(UTC)


def _to_domain(m: ESAPSubmissionModel) -> ESAPSubmission:
    return ESAPSubmission(
        id=m.id,
        organization_id=m.organization_id,
        report_year=m.report_year,
        export_format=m.export_format,
        status=m.status,
        submitted_at=m.submitted_at,
        submitted_by=m.submitted_by,
        confirmation_reference=m.confirmation_reference,
        notes=m.notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLESAPRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(self, organization_id: str) -> list[ESAPSubmission]:
        stmt = (
            select(ESAPSubmissionModel)
            .where(ESAPSubmissionModel.organization_id == organization_id)
            .order_by(ESAPSubmissionModel.report_year.desc())
        )
        return [_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, submission_id: str, organization_id: str) -> ESAPSubmission | None:
        m = self._s.get(ESAPSubmissionModel, submission_id)
        if not m or m.organization_id != organization_id:
            return None
        return _to_domain(m)

    def create(
        self,
        organization_id: str,
        report_year: int,
        export_format: str = "json",
        notes: str = "",
    ) -> ESAPSubmission:
        m = ESAPSubmissionModel(
            id=str(uuid4()),
            organization_id=organization_id,
            report_year=report_year,
            export_format=export_format,
            status=ESAPSubmissionStatus.DRAFT.value,
            notes=notes,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _to_domain(m)

    def mark_ready(self, submission_id: str, organization_id: str) -> ESAPSubmission | None:
        m = self._s.get(ESAPSubmissionModel, submission_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = ESAPSubmissionStatus.READY.value
        m.updated_at = _now()
        self._s.flush()
        return _to_domain(m)

    def mark_submitted(
        self,
        submission_id: str,
        organization_id: str,
        submitted_by: str,
        confirmation_reference: str,
    ) -> ESAPSubmission | None:
        m = self._s.get(ESAPSubmissionModel, submission_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = ESAPSubmissionStatus.SUBMITTED.value
        m.submitted_at = _now()
        m.submitted_by = submitted_by
        m.confirmation_reference = confirmation_reference
        m.updated_at = _now()
        self._s.flush()
        return _to_domain(m)
