"""Repositories for Scoping Study (CSDDD Art. 8 Abs. 3)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from domain.enums import ScopingStudyStatus
from domain.scoping import ScopingConfig, ScopingStudy
from infrastructure.persistence.models.scoping import (
    ScopingConfigAuditLogModel,
    ScopingConfigModel,
    ScopingStudyModel,
)
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel


def _loads(v: Optional[str]) -> list:
    if not v:
        return []
    try:
        return json.loads(v)
    except Exception:
        return []


def _dumps(v: list) -> str:
    return json.dumps(v or [])


def _config_to_domain(m: ScopingConfigModel) -> ScopingConfig:
    return ScopingConfig(
        id=m.id,
        organization_id=m.organization_id,
        version=m.version,
        risk_score_threshold_p1=m.risk_score_threshold_p1,
        risk_score_threshold_p2=m.risk_score_threshold_p2,
        high_risk_countries=_loads(m.high_risk_countries),
        high_risk_sectors=_loads(m.high_risk_sectors),
        revenue_threshold_pct=m.revenue_threshold_pct,
        notes=m.notes or "",
        created_by=m.created_by,
        created_at=m.created_at,
    )


def _study_to_domain(m: ScopingStudyModel) -> ScopingStudy:
    return ScopingStudy(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        report_year=m.report_year,
        config_id=m.config_id,
        status=m.status,
        results_snapshot=_loads(m.results_snapshot),
        methodology_notes=m.methodology_notes or "",
        submitted_at=m.submitted_at,
        submitted_by=m.submitted_by,
        approved_at=m.approved_at,
        approved_by=m.approved_by,
        next_review_due=m.next_review_due,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# Default best-practice config based on CSDDD guidelines
DEFAULT_HIGH_RISK_COUNTRIES = [
    "Bangladesh", "Myanmar", "Ethiopia", "Democratic Republic of Congo",
    "Nigeria", "Pakistan", "Cambodia", "Uzbekistan", "Turkmenistan",
    "Eritrea", "North Korea",
]

DEFAULT_HIGH_RISK_SECTORS = [
    "textiles", "apparel", "garment", "mining", "cobalt", "palm oil",
    "soy", "cattle", "cocoa", "coffee", "wood", "rubber",
    "electronics", "construction",
]


class SQLScopingConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, org_id: UUID) -> Optional[ScopingConfig]:
        m = (
            self.db.query(ScopingConfigModel)
            .filter(ScopingConfigModel.organization_id == org_id)
            .order_by(ScopingConfigModel.version.desc())
            .first()
        )
        return _config_to_domain(m) if m else None

    def list(self, org_id: UUID) -> list[ScopingConfig]:
        rows = (
            self.db.query(ScopingConfigModel)
            .filter(ScopingConfigModel.organization_id == org_id)
            .order_by(ScopingConfigModel.version.desc())
            .all()
        )
        return [_config_to_domain(m) for m in rows]

    def create(self, org_id: UUID, data: dict, created_by: str) -> ScopingConfig:
        latest = self.get_latest(org_id)
        next_version = (latest.version + 1) if latest else 1
        m = ScopingConfigModel(
            id=uuid4(),
            organization_id=org_id,
            version=next_version,
            risk_score_threshold_p1=data.get("risk_score_threshold_p1", 7.0),
            risk_score_threshold_p2=data.get("risk_score_threshold_p2", 4.0),
            high_risk_countries=_dumps(data.get("high_risk_countries", DEFAULT_HIGH_RISK_COUNTRIES)),
            high_risk_sectors=_dumps(data.get("high_risk_sectors", DEFAULT_HIGH_RISK_SECTORS)),
            revenue_threshold_pct=data.get("revenue_threshold_pct", 5.0),
            notes=data.get("notes", ""),
            created_by=created_by,
        )
        self.db.add(m)
        # Audit log
        self.db.add(ScopingConfigAuditLogModel(
            id=uuid4(),
            organization_id=org_id,
            config_id=m.id,
            action="created",
            performed_by=created_by,
            details=f"Version {next_version}",
        ))
        self.db.flush()
        return _config_to_domain(m)

    def create_default(self, org_id: UUID, created_by: str) -> ScopingConfig:
        return self.create(org_id, {}, created_by)


class SQLScopingStudyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, org_id: UUID, data: dict, results: list[dict]) -> ScopingStudy:
        m = ScopingStudyModel(
            id=uuid4(),
            organization_id=org_id,
            title=data["title"],
            report_year=data["report_year"],
            config_id=data["config_id"],
            status=ScopingStudyStatus.DRAFT.value,
            results_snapshot=_dumps(results),
            methodology_notes=data.get("methodology_notes", ""),
        )
        self.db.add(m)
        self.db.flush()
        return _study_to_domain(m)

    def get(self, study_id: UUID, org_id: UUID) -> Optional[ScopingStudy]:
        m = (
            self.db.query(ScopingStudyModel)
            .filter(ScopingStudyModel.id == study_id, ScopingStudyModel.organization_id == org_id)
            .first()
        )
        return _study_to_domain(m) if m else None

    def list_by_org(self, org_id: UUID, skip: int = 0, limit: int = 50) -> list[ScopingStudy]:
        rows = (
            self.db.query(ScopingStudyModel)
            .filter(ScopingStudyModel.organization_id == org_id)
            .order_by(ScopingStudyModel.report_year.desc(), ScopingStudyModel.created_at.desc())
            .offset(skip).limit(limit)
            .all()
        )
        return [_study_to_domain(m) for m in rows]

    def get_latest_approved(self, org_id: UUID) -> Optional[ScopingStudy]:
        m = (
            self.db.query(ScopingStudyModel)
            .filter(
                ScopingStudyModel.organization_id == org_id,
                ScopingStudyModel.status == ScopingStudyStatus.APPROVED.value,
            )
            .order_by(ScopingStudyModel.approved_at.desc())
            .first()
        )
        return _study_to_domain(m) if m else None

    def update_notes(self, study_id: UUID, org_id: UUID, notes: str) -> Optional[ScopingStudy]:
        m = (
            self.db.query(ScopingStudyModel)
            .filter(ScopingStudyModel.id == study_id, ScopingStudyModel.organization_id == org_id)
            .first()
        )
        if not m or m.status != ScopingStudyStatus.DRAFT.value:
            return None
        m.methodology_notes = notes
        self.db.flush()
        return _study_to_domain(m)

    def submit(self, study_id: UUID, org_id: UUID, submitted_by: str) -> Optional[ScopingStudy]:
        m = (
            self.db.query(ScopingStudyModel)
            .filter(ScopingStudyModel.id == study_id, ScopingStudyModel.organization_id == org_id)
            .first()
        )
        if not m:
            return None
        m.status = ScopingStudyStatus.SUBMITTED.value
        m.submitted_at = datetime.now(timezone.utc)
        m.submitted_by = submitted_by
        self.db.flush()
        return _study_to_domain(m)

    def approve(self, study_id: UUID, org_id: UUID, approved_by: str) -> Optional[ScopingStudy]:
        """HUMAN MANAGER/ADMIN ONLY — AI agents MUST NOT call this."""
        from dateutil.relativedelta import relativedelta
        m = (
            self.db.query(ScopingStudyModel)
            .filter(ScopingStudyModel.id == study_id, ScopingStudyModel.organization_id == org_id)
            .first()
        )
        if not m:
            return None
        now = datetime.now(timezone.utc)
        m.status = ScopingStudyStatus.APPROVED.value
        m.approved_at = now
        m.approved_by = approved_by
        m.next_review_due = now + relativedelta(years=1)
        self.db.flush()
        return _study_to_domain(m)

    def review_status(self, org_id: UUID) -> dict:
        latest = self.get_latest_approved(org_id)
        if not latest:
            return {"status": "no_study", "latest_approved_year": None, "next_review_due": None, "overdue": False}
        now = datetime.now(timezone.utc)
        overdue = latest.next_review_due is not None and latest.next_review_due < now
        days_until = None
        if latest.next_review_due:
            delta = latest.next_review_due - now
            days_until = delta.days
        return {
            "status": "overdue" if overdue else ("due_soon" if days_until is not None and days_until <= 30 else "current"),
            "latest_approved_year": latest.report_year,
            "next_review_due": latest.next_review_due.isoformat() if latest.next_review_due else None,
            "overdue": overdue,
            "days_until_review": days_until,
        }


class SQLScopingSupplierLoader:
    """Loads supplier data for the scoping analyzer from existing tables."""

    def __init__(self, db: Session):
        self.db = db

    def load(self, org_id: UUID) -> list[dict]:
        from application.scoping.scoping_analyzer import SupplierInput
        suppliers = (
            self.db.query(SupplierModel)
            .filter(SupplierModel.organization_id == str(org_id))
            .all()
        )
        results = []
        for s in suppliers:
            latest_score = (
                self.db.query(SupplierScoreModel)
                .filter(SupplierScoreModel.supplier_id == s.id)
                .order_by(SupplierScoreModel.created_at.desc())
                .first()
            )
            results.append({
                "supplier_id": str(s.id),
                "supplier_name": s.name,
                "country": s.country or "",
                "industry": s.industry or "",
                "risk_score": latest_score.risk_score if latest_score else 0.0,
                "risk_band": latest_score.risk_band if latest_score else "Low",
            })
        return results
