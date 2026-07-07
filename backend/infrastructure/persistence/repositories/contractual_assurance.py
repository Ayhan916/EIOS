"""Repositories — Contractual Assurance (CSDDD Art. 10)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.contractual_assurance import ClauseAuditLog, ContractAssurance, ContractClause
from domain.enums import AssuranceStatus, ClauseCategory
from infrastructure.persistence.models.contractual_assurance import (
    ClauseAuditLogModel,
    ContractAssuranceModel,
    ContractClauseModel,
)

# ── Default clause library ────────────────────────────────────────────────────

SEED_CLAUSES: list[dict] = [
    {
        "title": "Verbot von Kinderarbeit",
        "clause_text": (
            "Der Lieferant stellt sicher, dass in seiner Lieferkette keine Kinderarbeit "
            "im Sinne der ILO-Kernarbeitsnormen (Konventionen 138 & 182) eingesetzt wird."
        ),
        "category": ClauseCategory.LABOR_RIGHTS.value,
        "cascade_required": True,
        "is_mandatory": True,
    },
    {
        "title": "Verbot von Zwangsarbeit",
        "clause_text": (
            "Jede Form von Zwangs-, Schuldknechtschafts- oder Pflichtarbeit ist verboten. "
            "Der Lieferant garantiert, dass alle Arbeitsverhältnisse auf freiwilliger Basis beruhen."
        ),
        "category": ClauseCategory.LABOR_RIGHTS.value,
        "cascade_required": True,
        "is_mandatory": True,
    },
    {
        "title": "Diskriminierungsverbot & Chancengleichheit",
        "clause_text": (
            "Der Lieferant diskriminiert nicht aufgrund von Geschlecht, Rasse, Religion, "
            "Nationalität, Behinderung oder anderen geschützten Merkmalen."
        ),
        "category": ClauseCategory.HUMAN_RIGHTS.value,
        "cascade_required": False,
        "is_mandatory": True,
    },
    {
        "title": "Vereinigungsfreiheit & Kollektivverhandlungen",
        "clause_text": (
            "Der Lieferant respektiert das Recht der Beschäftigten auf Vereinigungsfreiheit "
            "und erkennt Kollektivverhandlungen gemäß ILO-Konvention 87 & 98 an."
        ),
        "category": ClauseCategory.LABOR_RIGHTS.value,
        "cascade_required": False,
        "is_mandatory": True,
    },
    {
        "title": "Umwelt-Mindeststandards",
        "clause_text": (
            "Der Lieferant hält alle anwendbaren Umweltgesetze ein und trifft Maßnahmen "
            "zur Minimierung von Emissionen, Abfall und Ressourcenverbrauch."
        ),
        "category": ClauseCategory.ENVIRONMENT.value,
        "cascade_required": True,
        "is_mandatory": True,
    },
    {
        "title": "Verbot gefährlicher Stoffe & Chemikalien",
        "clause_text": (
            "Der Lieferant verwendet keine gemäß REACH oder RoHS verbotenen Substanzen "
            "und führt ein aktuelles Chemikalienregister."
        ),
        "category": ClauseCategory.ENVIRONMENT.value,
        "cascade_required": False,
        "is_mandatory": False,
    },
    {
        "title": "Antikorruption & Bestechungsverbot",
        "clause_text": (
            "Der Lieferant unterhält keine Korruption, Bestechung oder unlautere Zahlungen "
            "gegenüber öffentlichen Stellen oder Privatpersonen und hält den UN Global Compact "
            "Prinzip 10 ein."
        ),
        "category": ClauseCategory.ANTI_CORRUPTION.value,
        "cascade_required": True,
        "is_mandatory": True,
    },
    {
        "title": "Arbeitssicherheit & Gesundheitsschutz",
        "clause_text": (
            "Der Lieferant stellt sichere Arbeitsbedingungen sicher (ILO-Konvention 155) "
            "und führt ein Unfallmelde- und Präventionsprogramm."
        ),
        "category": ClauseCategory.HEALTH_SAFETY.value,
        "cascade_required": False,
        "is_mandatory": True,
    },
    {
        "title": "Datenschutz & DSGVO-Konformität",
        "clause_text": (
            "Der Lieferant verarbeitet personenbezogene Daten ausschließlich gemäß DSGVO "
            "und schließt mit dem Auftraggeber einen Auftragsverarbeitungsvertrag ab."
        ),
        "category": ClauseCategory.DATA_PROTECTION.value,
        "cascade_required": False,
        "is_mandatory": False,
    },
    {
        "title": "Cascading-Pflicht (Weitergabe)",
        "clause_text": (
            "Der Lieferant verpflichtet seine eigenen Lieferanten vertraglich zu gleichwertigen "
            "Sorgfaltspflicht-Standards und weist dies auf Anfrage nach."
        ),
        "category": ClauseCategory.OTHER.value,
        "cascade_required": True,
        "is_mandatory": True,
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


def _clause_to_domain(m: ContractClauseModel) -> ContractClause:
    return ContractClause(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        clause_text=m.clause_text,
        category=m.category,
        cascade_required=m.cascade_required,
        is_mandatory=m.is_mandatory,
        version=m.version,
        is_active=m.is_active,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _assurance_to_domain(m: ContractAssuranceModel) -> ContractAssurance:
    return ContractAssurance(
        id=m.id,
        organization_id=m.organization_id,
        supplier_id=m.supplier_id,
        clause_id=m.clause_id,
        status=m.status,
        accepted_at=m.accepted_at,
        accepted_by=m.accepted_by,
        document_ref=m.document_ref,
        notes=m.notes,
        cascade_confirmed=m.cascade_confirmed,
        cascade_confirmed_at=m.cascade_confirmed_at,
        valid_until=m.valid_until,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _log_to_domain(m: ClauseAuditLogModel) -> ClauseAuditLog:
    return ClauseAuditLog(
        id=m.id,
        organization_id=m.organization_id,
        assurance_id=m.assurance_id,
        changed_by=m.changed_by,
        from_status=m.from_status,
        to_status=m.to_status,
        note=m.note,
        created_at=m.created_at,
    )


# ── Clause Repository ─────────────────────────────────────────────────────────


class SQLContractClauseRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(self, organization_id: str, active_only: bool = True) -> list[ContractClause]:
        stmt = select(ContractClauseModel).where(
            ContractClauseModel.organization_id == organization_id
        )
        if active_only:
            stmt = stmt.where(ContractClauseModel.is_active == True)  # noqa: E712
        stmt = stmt.order_by(ContractClauseModel.category, ContractClauseModel.title)
        return [_clause_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, clause_id: str, organization_id: str) -> ContractClause | None:
        m = self._s.get(ContractClauseModel, clause_id)
        if not m or m.organization_id != organization_id:
            return None
        return _clause_to_domain(m)

    def create(
        self,
        organization_id: str,
        title: str,
        clause_text: str,
        category: str,
        cascade_required: bool,
        is_mandatory: bool,
        version: str,
        created_by: str,
    ) -> ContractClause:
        m = ContractClauseModel(
            id=str(uuid4()),
            organization_id=organization_id,
            title=title,
            clause_text=clause_text,
            category=category,
            cascade_required=cascade_required,
            is_mandatory=is_mandatory,
            version=version,
            is_active=True,
            created_by=created_by,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _clause_to_domain(m)

    def update(self, clause_id: str, organization_id: str, **fields) -> ContractClause | None:
        m = self._s.get(ContractClauseModel, clause_id)
        if not m or m.organization_id != organization_id:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(m, k):
                setattr(m, k, v)
        m.updated_at = _now()
        self._s.flush()
        return _clause_to_domain(m)

    def seed_defaults(self, organization_id: str, created_by: str) -> int:
        """Seed the 10 best-practice clauses. Skip titles that already exist."""
        existing_titles = {
            r[0]
            for r in self._s.execute(
                select(ContractClauseModel.title).where(
                    ContractClauseModel.organization_id == organization_id
                )
            ).all()
        }
        count = 0
        for c in SEED_CLAUSES:
            if c["title"] not in existing_titles:
                self._s.add(
                    ContractClauseModel(
                        id=str(uuid4()),
                        organization_id=organization_id,
                        title=c["title"],
                        clause_text=c["clause_text"],
                        category=c["category"],
                        cascade_required=c["cascade_required"],
                        is_mandatory=c["is_mandatory"],
                        version="1.0",
                        is_active=True,
                        created_by=created_by,
                        created_at=_now(),
                        updated_at=_now(),
                    )
                )
                count += 1
        self._s.flush()
        return count

    def summary(self, organization_id: str) -> dict:
        clauses = self.list_org(organization_id, active_only=False)
        return {
            "total": len(clauses),
            "active": sum(1 for c in clauses if c.is_active),
            "mandatory": sum(1 for c in clauses if c.is_mandatory),
            "cascade_required": sum(1 for c in clauses if c.cascade_required),
            "by_category": {
                cat.value: sum(1 for c in clauses if c.category == cat.value)
                for cat in ClauseCategory
            },
        }


# ── Assurance Repository ──────────────────────────────────────────────────────


class SQLContractAssuranceRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(
        self,
        organization_id: str,
        supplier_id: str | None = None,
        clause_id: str | None = None,
        status: str | None = None,
    ) -> list[ContractAssurance]:
        stmt = select(ContractAssuranceModel).where(
            ContractAssuranceModel.organization_id == organization_id
        )
        if supplier_id:
            stmt = stmt.where(ContractAssuranceModel.supplier_id == supplier_id)
        if clause_id:
            stmt = stmt.where(ContractAssuranceModel.clause_id == clause_id)
        if status:
            stmt = stmt.where(ContractAssuranceModel.status == status)
        stmt = stmt.order_by(ContractAssuranceModel.created_at.desc())
        return [_assurance_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, assurance_id: str, organization_id: str) -> ContractAssurance | None:
        m = self._s.get(ContractAssuranceModel, assurance_id)
        if not m or m.organization_id != organization_id:
            return None
        return _assurance_to_domain(m)

    def create(
        self,
        organization_id: str,
        supplier_id: str,
        clause_id: str,
        document_ref: str | None,
        notes: str | None,
        valid_until: datetime | None,
    ) -> ContractAssurance:
        m = ContractAssuranceModel(
            id=str(uuid4()),
            organization_id=organization_id,
            supplier_id=supplier_id,
            clause_id=clause_id,
            status=AssuranceStatus.PENDING.value,
            accepted_at=None,
            accepted_by=None,
            document_ref=document_ref,
            notes=notes,
            cascade_confirmed=False,
            cascade_confirmed_at=None,
            valid_until=valid_until,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _assurance_to_domain(m)

    def accept(
        self, assurance_id: str, organization_id: str, accepted_by: str, document_ref: str | None
    ) -> ContractAssurance | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(ContractAssuranceModel, assurance_id)
        if not m or m.organization_id != organization_id:
            return None
        old_status = m.status
        m.status = AssuranceStatus.ACCEPTED.value
        m.accepted_at = _now()
        m.accepted_by = accepted_by
        if document_ref:
            m.document_ref = document_ref
        m.updated_at = _now()
        self._s.add(
            ClauseAuditLogModel(
                id=str(uuid4()),
                organization_id=organization_id,
                assurance_id=assurance_id,
                changed_by=accepted_by,
                from_status=old_status,
                to_status=AssuranceStatus.ACCEPTED.value,
                note="Accepted by analyst",
                created_at=_now(),
            )
        )
        self._s.flush()
        return _assurance_to_domain(m)

    def update_status(
        self,
        assurance_id: str,
        organization_id: str,
        new_status: str,
        changed_by: str,
        note: str | None,
    ) -> ContractAssurance | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(ContractAssuranceModel, assurance_id)
        if not m or m.organization_id != organization_id:
            return None
        old_status = m.status
        m.status = new_status
        m.updated_at = _now()
        self._s.add(
            ClauseAuditLogModel(
                id=str(uuid4()),
                organization_id=organization_id,
                assurance_id=assurance_id,
                changed_by=changed_by,
                from_status=old_status,
                to_status=new_status,
                note=note,
                created_at=_now(),
            )
        )
        self._s.flush()
        return _assurance_to_domain(m)

    def confirm_cascade(
        self, assurance_id: str, organization_id: str, confirmed_by: str
    ) -> ContractAssurance | None:
        """HUMAN ANALYST/ADMIN ONLY — AI agents MUST NOT call this method."""
        m = self._s.get(ContractAssuranceModel, assurance_id)
        if not m or m.organization_id != organization_id:
            return None
        m.cascade_confirmed = True
        m.cascade_confirmed_at = _now()
        m.updated_at = _now()
        self._s.add(
            ClauseAuditLogModel(
                id=str(uuid4()),
                organization_id=organization_id,
                assurance_id=assurance_id,
                changed_by=confirmed_by,
                from_status=m.status,
                to_status=m.status,
                note="Cascade obligation confirmed",
                created_at=_now(),
            )
        )
        self._s.flush()
        return _assurance_to_domain(m)

    def audit_logs(self, assurance_id: str, organization_id: str) -> list[ClauseAuditLog]:
        stmt = (
            select(ClauseAuditLogModel)
            .where(
                ClauseAuditLogModel.assurance_id == assurance_id,
                ClauseAuditLogModel.organization_id == organization_id,
            )
            .order_by(ClauseAuditLogModel.created_at.desc())
        )
        return [_log_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def dashboard(self, organization_id: str) -> dict:
        """Aggregate assurance compliance metrics for dashboard KPIs."""
        all_a = self.list_org(organization_id)
        total = len(all_a)
        accepted = sum(1 for a in all_a if a.status == AssuranceStatus.ACCEPTED.value)
        pending = sum(1 for a in all_a if a.status == AssuranceStatus.PENDING.value)
        rejected = sum(1 for a in all_a if a.status == AssuranceStatus.REJECTED.value)
        expired = sum(1 for a in all_a if a.status == AssuranceStatus.EXPIRED.value)
        cascade_req = sum(1 for a in all_a if not a.cascade_confirmed)
        acceptance_rate = round((accepted / total * 100) if total else 0, 1)
        return {
            "total": total,
            "accepted": accepted,
            "pending": pending,
            "rejected": rejected,
            "expired": expired,
            "cascade_unconfirmed": cascade_req,
            "acceptance_rate_pct": acceptance_rate,
        }

    def supplier_coverage(self, organization_id: str) -> list[dict]:
        """Per-supplier assurance summary — which suppliers have pending/rejected clauses."""
        all_a = self.list_org(organization_id)
        by_supplier: dict[str, dict] = {}
        for a in all_a:
            if a.supplier_id not in by_supplier:
                by_supplier[a.supplier_id] = {
                    "supplier_id": a.supplier_id,
                    "total": 0,
                    "accepted": 0,
                    "pending": 0,
                    "rejected": 0,
                }
            by_supplier[a.supplier_id]["total"] += 1
            by_supplier[a.supplier_id][a.status] = by_supplier[a.supplier_id].get(a.status, 0) + 1
        return list(by_supplier.values())
