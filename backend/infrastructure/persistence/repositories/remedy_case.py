"""Repositories for Remedy Case Manager (CSDDD Art. 12)."""

from __future__ import annotations

import json
from datetime import UTC
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from domain.enums import RemedyCaseStatus
from domain.remedy_case import RemedyAction, RemedyAuditLog, RemedyBeneficiary, RemedyCase
from infrastructure.persistence.models.remedy_case import (
    RemedyActionModel,
    RemedyAuditLogModel,
    RemedyBeneficiaryModel,
    RemedyCaseModel,
)


def _loads(v: str | None) -> list:
    if not v:
        return []
    try:
        return json.loads(v)
    except Exception:
        return []


def _dumps(v: list) -> str:
    return json.dumps(v or [])


def _to_domain(m: RemedyCaseModel) -> RemedyCase:
    return RemedyCase(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        description=m.description or "",
        incident_date=m.incident_date,
        affected_count=m.affected_count,
        affected_type=m.affected_type,
        rights=_loads(m.rights),
        remedy_types=_loads(m.remedy_types),
        severity_score=m.severity_score,
        impact_causation=m.impact_causation,
        status=m.status,
        source_grievance_id=m.source_grievance_id,
        co_responsible_parties=_loads(m.co_responsible_parties),
        closed_at=m.closed_at,
        closed_by=m.closed_by,
        closure_notes=m.closure_notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _ben_to_domain(m: RemedyBeneficiaryModel) -> RemedyBeneficiary:
    return RemedyBeneficiary(
        id=m.id,
        remedy_case_id=m.remedy_case_id,
        reference=m.reference,
        affected_type=m.affected_type,
        promised_compensation=m.promised_compensation,
        received_compensation=m.received_compensation,
        confirmation_date=m.confirmation_date,
        created_at=m.created_at,
    )


def _action_to_domain(m: RemedyActionModel) -> RemedyAction:
    return RemedyAction(
        id=m.id,
        remedy_case_id=m.remedy_case_id,
        title=m.title,
        description=m.description or "",
        status=m.status,
        responsible_party=m.responsible_party,
        due_date=m.due_date,
        completed_at=m.completed_at,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _log_to_domain(m: RemedyAuditLogModel) -> RemedyAuditLog:
    return RemedyAuditLog(
        id=m.id,
        remedy_case_id=m.remedy_case_id,
        action=m.action,
        performed_by=m.performed_by,
        details=m.details,
        created_at=m.created_at,
    )


class SQLRemedyCaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, org_id: UUID, data: dict) -> RemedyCase:
        m = RemedyCaseModel(
            id=uuid4(),
            organization_id=org_id,
            title=data["title"],
            description=data.get("description"),
            incident_date=data["incident_date"],
            affected_count=data.get("affected_count", 0),
            affected_type=data["affected_type"],
            rights=_dumps(data.get("rights", [])),
            remedy_types=_dumps(data.get("remedy_types", [])),
            severity_score=data.get("severity_score", 0.0),
            impact_causation=data["impact_causation"],
            status=RemedyCaseStatus.OPEN.value,
            source_grievance_id=data.get("source_grievance_id"),
            co_responsible_parties=_dumps(data.get("co_responsible_parties", [])),
        )
        self.db.add(m)
        self.db.flush()
        return _to_domain(m)

    def get(self, case_id: UUID, org_id: UUID) -> RemedyCase | None:
        m = (
            self.db.query(RemedyCaseModel)
            .filter(RemedyCaseModel.id == case_id, RemedyCaseModel.organization_id == org_id)
            .first()
        )
        return _to_domain(m) if m else None

    def list_by_org(
        self,
        org_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[RemedyCase]:
        q = self.db.query(RemedyCaseModel).filter(RemedyCaseModel.organization_id == org_id)
        if status:
            q = q.filter(RemedyCaseModel.status == status)
        q = q.order_by(RemedyCaseModel.created_at.desc()).offset(skip).limit(limit)
        return [_to_domain(m) for m in q.all()]

    def count_by_org(self, org_id: UUID) -> int:
        return (
            self.db.query(RemedyCaseModel).filter(RemedyCaseModel.organization_id == org_id).count()
        )

    def update(self, case_id: UUID, org_id: UUID, data: dict) -> RemedyCase | None:
        m = (
            self.db.query(RemedyCaseModel)
            .filter(RemedyCaseModel.id == case_id, RemedyCaseModel.organization_id == org_id)
            .first()
        )
        if not m:
            return None
        for k, v in data.items():
            if k in ("rights", "remedy_types", "co_responsible_parties") and isinstance(v, list):
                setattr(m, k, _dumps(v))
            elif hasattr(m, k):
                setattr(m, k, v)
        self.db.flush()
        return _to_domain(m)

    def close(
        self, case_id: UUID, org_id: UUID, closed_by: str, notes: str | None
    ) -> RemedyCase | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this."""
        from datetime import datetime

        m = (
            self.db.query(RemedyCaseModel)
            .filter(RemedyCaseModel.id == case_id, RemedyCaseModel.organization_id == org_id)
            .first()
        )
        if not m:
            return None
        m.status = RemedyCaseStatus.COMPLETED.value
        m.closed_at = datetime.now(UTC)
        m.closed_by = closed_by
        m.closure_notes = notes
        self.db.flush()
        return _to_domain(m)

    def remedy_summary(self, org_id: UUID, year: int) -> dict:
        from datetime import datetime

        start = datetime(year, 1, 1, tzinfo=UTC)
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
        cases = (
            self.db.query(RemedyCaseModel)
            .filter(
                RemedyCaseModel.organization_id == org_id,
                RemedyCaseModel.incident_date >= start,
                RemedyCaseModel.incident_date < end,
            )
            .all()
        )
        return {
            "year": year,
            "total": len(cases),
            "by_status": {
                s.value: sum(1 for c in cases if c.status == s.value) for s in RemedyCaseStatus
            },
            "by_affected_type": _aggregate_list([c.affected_type for c in cases]),
            "total_affected_persons": sum(c.affected_count for c in cases),
            "avg_severity": round(sum(c.severity_score for c in cases) / len(cases), 2)
            if cases
            else 0.0,
        }


def _aggregate_list(items: list) -> dict:
    result: dict = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result


class SQLRemedyBeneficiaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, remedy_case_id: UUID, data: dict) -> RemedyBeneficiary:
        m = RemedyBeneficiaryModel(
            id=uuid4(),
            remedy_case_id=remedy_case_id,
            reference=data["reference"],
            affected_type=data["affected_type"],
            promised_compensation=data.get("promised_compensation"),
            received_compensation=data.get("received_compensation"),
            confirmation_date=data.get("confirmation_date"),
        )
        self.db.add(m)
        self.db.flush()
        return _ben_to_domain(m)

    def list_by_case(self, remedy_case_id: UUID) -> list[RemedyBeneficiary]:
        return [
            _ben_to_domain(m)
            for m in self.db.query(RemedyBeneficiaryModel)
            .filter(RemedyBeneficiaryModel.remedy_case_id == remedy_case_id)
            .all()
        ]

    def update(self, ben_id: UUID, data: dict) -> RemedyBeneficiary | None:
        m = (
            self.db.query(RemedyBeneficiaryModel)
            .filter(RemedyBeneficiaryModel.id == ben_id)
            .first()
        )
        if not m:
            return None
        for k, v in data.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self.db.flush()
        return _ben_to_domain(m)


class SQLRemedyActionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, remedy_case_id: UUID, data: dict, created_by: str) -> RemedyAction:
        m = RemedyActionModel(
            id=uuid4(),
            remedy_case_id=remedy_case_id,
            title=data["title"],
            description=data.get("description"),
            status="todo",
            responsible_party=data.get("responsible_party"),
            due_date=data.get("due_date"),
            created_by=created_by,
        )
        self.db.add(m)
        self.db.flush()
        return _action_to_domain(m)

    def list_by_case(self, remedy_case_id: UUID) -> list[RemedyAction]:
        return [
            _action_to_domain(m)
            for m in self.db.query(RemedyActionModel)
            .filter(RemedyActionModel.remedy_case_id == remedy_case_id)
            .order_by(RemedyActionModel.created_at)
            .all()
        ]

    def update(self, action_id: UUID, data: dict) -> RemedyAction | None:
        from datetime import datetime

        m = self.db.query(RemedyActionModel).filter(RemedyActionModel.id == action_id).first()
        if not m:
            return None
        for k, v in data.items():
            if hasattr(m, k):
                setattr(m, k, v)
        if data.get("status") == "done" and not m.completed_at:
            m.completed_at = datetime.now(UTC)
        self.db.flush()
        return _action_to_domain(m)


class SQLRemedyAuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self, remedy_case_id: UUID, action: str, performed_by: str, details: str | None = None
    ) -> None:
        m = RemedyAuditLogModel(
            id=uuid4(),
            remedy_case_id=remedy_case_id,
            action=action,
            performed_by=performed_by,
            details=details,
        )
        self.db.add(m)
        self.db.flush()

    def list_by_case(self, remedy_case_id: UUID) -> list[RemedyAuditLog]:
        return [
            _log_to_domain(m)
            for m in self.db.query(RemedyAuditLogModel)
            .filter(RemedyAuditLogModel.remedy_case_id == remedy_case_id)
            .order_by(RemedyAuditLogModel.created_at.desc())
            .all()
        ]
