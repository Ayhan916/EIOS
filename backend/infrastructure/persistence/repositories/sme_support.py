"""Repositories — SME Support Tracker (CSDDD Art. 10 Abs. 2 lit. b)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.enums import SMEClassification, SupportMeasureStatus, SupportProgramStatus
from domain.sme_support import SMEProfile, SupportMeasure, SupportProgram
from infrastructure.persistence.models.sme_support import (
    SMEProfileModel,
    SupportMeasureModel,
    SupportProgramModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _classify(employees: int | None, revenue: float | None) -> str:
    """Deterministic EU SME classification (Rec. 2003/361/EC)."""
    e = employees or 0
    r = revenue or 0.0
    if e < 10 and r <= 2_000_000:
        return SMEClassification.MICRO.value
    if e < 50 and r <= 10_000_000:
        return SMEClassification.SMALL.value
    if e < 250 and r <= 50_000_000:
        return SMEClassification.MEDIUM.value
    return SMEClassification.LARGE.value


# ── Converters ────────────────────────────────────────────────────────────────


def _profile_to_domain(m: SMEProfileModel) -> SMEProfile:
    return SMEProfile(
        id=m.id,
        organization_id=m.organization_id,
        supplier_id=m.supplier_id,
        classification=m.classification,
        employee_count=m.employee_count,
        annual_revenue_eur=m.annual_revenue_eur,
        is_confirmed=m.is_confirmed,
        confirmed_by=m.confirmed_by,
        confirmed_at=m.confirmed_at,
        notes=m.notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _program_to_domain(m: SupportProgramModel) -> SupportProgram:
    return SupportProgram(
        id=m.id,
        organization_id=m.organization_id,
        supplier_id=m.supplier_id,
        title=m.title,
        description=m.description,
        status=m.status,
        start_date=m.start_date,
        end_date=m.end_date,
        responsible_user=m.responsible_user,
        total_budget_eur=m.total_budget_eur,
        spent_budget_eur=m.spent_budget_eur,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _measure_to_domain(m: SupportMeasureModel) -> SupportMeasure:
    return SupportMeasure(
        id=m.id,
        organization_id=m.organization_id,
        program_id=m.program_id,
        title=m.title,
        support_type=m.support_type,
        status=m.status,
        description=m.description,
        due_date=m.due_date,
        completed_at=m.completed_at,
        cost_eur=m.cost_eur,
        impact_notes=m.impact_notes,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── SMEProfile Repository ─────────────────────────────────────────────────────


class SQLSMEProfileRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(self, organization_id: str, sme_only: bool = True) -> list[SMEProfile]:
        stmt = select(SMEProfileModel).where(SMEProfileModel.organization_id == organization_id)
        if sme_only:
            stmt = stmt.where(SMEProfileModel.classification != SMEClassification.LARGE.value)
        stmt = stmt.order_by(SMEProfileModel.classification, SMEProfileModel.supplier_id)
        return [_profile_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get_by_supplier(self, organization_id: str, supplier_id: str) -> SMEProfile | None:
        stmt = select(SMEProfileModel).where(
            SMEProfileModel.organization_id == organization_id,
            SMEProfileModel.supplier_id == supplier_id,
        )
        m = self._s.execute(stmt).scalar_one_or_none()
        return _profile_to_domain(m) if m else None

    def upsert(
        self,
        organization_id: str,
        supplier_id: str,
        employee_count: int | None,
        annual_revenue_eur: float | None,
        notes: str | None,
        created_by: str,
    ) -> SMEProfile:
        existing = self.get_by_supplier(organization_id, supplier_id)
        classification = _classify(employee_count, annual_revenue_eur)
        if existing:
            m = self._s.get(SMEProfileModel, existing.id)
            m.employee_count = employee_count
            m.annual_revenue_eur = annual_revenue_eur
            m.classification = classification
            m.notes = notes
            m.updated_at = _now()
        else:
            m = SMEProfileModel(
                id=str(uuid4()),
                organization_id=organization_id,
                supplier_id=supplier_id,
                classification=classification,
                employee_count=employee_count,
                annual_revenue_eur=annual_revenue_eur,
                is_confirmed=False,
                confirmed_by=None,
                confirmed_at=None,
                notes=notes,
                created_at=_now(),
                updated_at=_now(),
            )
            self._s.add(m)
        self._s.flush()
        return _profile_to_domain(m)

    def confirm(
        self, organization_id: str, supplier_id: str, confirmed_by: str
    ) -> SMEProfile | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        p = self.get_by_supplier(organization_id, supplier_id)
        if not p:
            return None
        m = self._s.get(SMEProfileModel, p.id)
        m.is_confirmed = True
        m.confirmed_by = confirmed_by
        m.confirmed_at = _now()
        m.updated_at = _now()
        self._s.flush()
        return _profile_to_domain(m)

    def summary(self, organization_id: str) -> dict:
        profiles = self.list_org(organization_id, sme_only=False)
        by_cls: dict[str, int] = {}
        for p in profiles:
            by_cls[p.classification] = by_cls.get(p.classification, 0) + 1
        total_sme = sum(v for k, v in by_cls.items() if k != SMEClassification.LARGE.value)
        return {
            "total": len(profiles),
            "sme_count": total_sme,
            "confirmed": sum(1 for p in profiles if p.is_confirmed),
            "by_classification": by_cls,
        }


# ── SupportProgram Repository ─────────────────────────────────────────────────


class SQLSupportProgramRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(
        self,
        organization_id: str,
        supplier_id: str | None = None,
        status: str | None = None,
    ) -> list[SupportProgram]:
        stmt = select(SupportProgramModel).where(
            SupportProgramModel.organization_id == organization_id
        )
        if supplier_id:
            stmt = stmt.where(SupportProgramModel.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(SupportProgramModel.status == status)
        stmt = stmt.order_by(SupportProgramModel.created_at.desc())
        return [_program_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, program_id: str, organization_id: str) -> SupportProgram | None:
        m = self._s.get(SupportProgramModel, program_id)
        if not m or m.organization_id != organization_id:
            return None
        return _program_to_domain(m)

    def create(
        self,
        organization_id: str,
        supplier_id: str,
        title: str,
        description: str,
        start_date: datetime | None,
        end_date: datetime | None,
        responsible_user: str | None,
        total_budget_eur: float | None,
        created_by: str,
    ) -> SupportProgram:
        m = SupportProgramModel(
            id=str(uuid4()),
            organization_id=organization_id,
            supplier_id=supplier_id,
            title=title,
            description=description,
            status=SupportProgramStatus.DRAFT.value,
            start_date=start_date,
            end_date=end_date,
            responsible_user=responsible_user,
            total_budget_eur=total_budget_eur,
            spent_budget_eur=0.0,
            created_by=created_by,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _program_to_domain(m)

    def activate(self, program_id: str, organization_id: str) -> SupportProgram | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(SupportProgramModel, program_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = SupportProgramStatus.ACTIVE.value
        m.updated_at = _now()
        self._s.flush()
        return _program_to_domain(m)

    def complete(self, program_id: str, organization_id: str) -> SupportProgram | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(SupportProgramModel, program_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = SupportProgramStatus.COMPLETED.value
        m.updated_at = _now()
        self._s.flush()
        return _program_to_domain(m)

    def update(self, program_id: str, organization_id: str, **fields) -> SupportProgram | None:
        m = self._s.get(SupportProgramModel, program_id)
        if not m or m.organization_id != organization_id:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(m, k):
                setattr(m, k, v)
        m.updated_at = _now()
        self._s.flush()
        return _program_to_domain(m)

    def recalculate_spent(self, program_id: str) -> None:
        """Recompute spent_budget_eur from completed measures."""
        stmt = select(SupportMeasureModel).where(
            SupportMeasureModel.program_id == program_id,
            SupportMeasureModel.status == SupportMeasureStatus.COMPLETED.value,
        )
        measures = self._s.execute(stmt).scalars().all()
        total = sum(m.cost_eur or 0.0 for m in measures)
        prog = self._s.get(SupportProgramModel, program_id)
        if prog:
            prog.spent_budget_eur = total
            prog.updated_at = _now()
        self._s.flush()

    def annual_report(self, organization_id: str, year: int) -> dict:
        """Aggregate support data for CSDDD annual report (Art. 16)."""
        all_programs = self.list_org(organization_id)
        year_programs = [p for p in all_programs if p.start_date and p.start_date.year == year]
        total_invested = sum(p.spent_budget_eur for p in year_programs)
        completed = sum(
            1 for p in year_programs if p.status == SupportProgramStatus.COMPLETED.value
        )
        return {
            "year": year,
            "programs_total": len(year_programs),
            "programs_completed": completed,
            "total_invested_eur": round(total_invested, 2),
            "sme_suppliers_supported": len({p.supplier_id for p in year_programs}),
        }


# ── SupportMeasure Repository ─────────────────────────────────────────────────


class SQLSupportMeasureRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_program(self, program_id: str, organization_id: str) -> list[SupportMeasure]:
        stmt = (
            select(SupportMeasureModel)
            .where(
                SupportMeasureModel.program_id == program_id,
                SupportMeasureModel.organization_id == organization_id,
            )
            .order_by(
                SupportMeasureModel.due_date.asc().nulls_last(), SupportMeasureModel.created_at
            )
        )
        return [_measure_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, measure_id: str, organization_id: str) -> SupportMeasure | None:
        m = self._s.get(SupportMeasureModel, measure_id)
        if not m or m.organization_id != organization_id:
            return None
        return _measure_to_domain(m)

    def create(
        self,
        organization_id: str,
        program_id: str,
        title: str,
        support_type: str,
        description: str | None,
        due_date: datetime | None,
        cost_eur: float | None,
    ) -> SupportMeasure:
        m = SupportMeasureModel(
            id=str(uuid4()),
            organization_id=organization_id,
            program_id=program_id,
            title=title,
            support_type=support_type,
            status=SupportMeasureStatus.PLANNED.value,
            description=description,
            due_date=due_date,
            completed_at=None,
            cost_eur=cost_eur,
            impact_notes=None,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _measure_to_domain(m)

    def complete(
        self, measure_id: str, organization_id: str, impact_notes: str | None
    ) -> SupportMeasure | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(SupportMeasureModel, measure_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = SupportMeasureStatus.COMPLETED.value
        m.completed_at = _now()
        m.impact_notes = impact_notes
        m.updated_at = _now()
        self._s.flush()
        # Recalculate parent program spent budget
        SQLSupportProgramRepository(self._s).recalculate_spent(m.program_id)
        return _measure_to_domain(m)

    def update_status(
        self, measure_id: str, organization_id: str, new_status: str
    ) -> SupportMeasure | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(SupportMeasureModel, measure_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = new_status
        if new_status == SupportMeasureStatus.COMPLETED.value and not m.completed_at:
            m.completed_at = _now()
        m.updated_at = _now()
        self._s.flush()
        SQLSupportProgramRepository(self._s).recalculate_spent(m.program_id)
        return _measure_to_domain(m)
