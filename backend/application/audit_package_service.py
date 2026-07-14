"""AuditPackage Generator Service (E5-F2).

Assembles a complete audit evidence bundle for a supplier over a given period.
Reads from: assessments, findings, risks, finding_evidence_links, audit_events,
            supplier_scores, prompt_versions.

No LLM. No writes. Pure read aggregation.

Usage:
    service = AuditPackageService(session, settings)
    package = await service.generate(
        supplier_id="sup-123",
        period_from=datetime(2025, 1, 1, tzinfo=UTC),
        period_to=datetime(2025, 12, 31, tzinfo=UTC),
    )
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.prompt_registry import PromptRegistry
from application.scoring.risk_score_calculator import FORMULA_VERSION, calculate
from application.scoring.supplier_scorer import ScoreInputs
from domain.audit_package import AuditPackage, MethodologySnapshot
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.finding_evidence_link import FindingEvidenceLinkModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel

_GENERATOR_VERSION = "AuditPackage-v1.0"

# Names of prompts whose active versions are included in methodology snapshot
_TRACKED_PROMPTS = ("financial_extraction_system", "esg_extraction_system")


class AuditPackageService:
    """Assemble a complete audit package for one supplier in a given period."""

    def __init__(self, session: AsyncSession, extraction_model: str, main_model: str) -> None:
        self._session = session
        self._extraction_model = extraction_model
        self._main_model = main_model

    async def generate(
        self,
        supplier_id: str,
        period_from: datetime,
        period_to: datetime,
    ) -> AuditPackage:
        """Assemble and return an immutable AuditPackage."""
        session = self._session

        # ── Assessment IDs in period ──────────────────────────────────────────
        assessment_rows = (
            await session.execute(
                select(AssessmentModel.id)
                .where(
                    AssessmentModel.supplier_id == supplier_id,
                    AssessmentModel.status != "Deleted",
                    AssessmentModel.created_at >= period_from,
                    AssessmentModel.created_at <= period_to,
                )
            )
        ).scalars().all()
        assessment_ids = tuple(assessment_rows)

        # ── Findings count ────────────────────────────────────────────────────
        findings_count = 0
        evidence_count = 0
        if assessment_ids:
            findings_count = (
                await session.execute(
                    select(func.count(FindingModel.id)).where(
                        FindingModel.assessment_id.in_(assessment_ids),
                        FindingModel.status != "Deleted",
                    )
                )
            ).scalar_one()

            # ── Evidence links count ──────────────────────────────────────────
            finding_ids = (
                await session.execute(
                    select(FindingModel.id).where(
                        FindingModel.assessment_id.in_(assessment_ids),
                        FindingModel.status != "Deleted",
                    )
                )
            ).scalars().all()

            if finding_ids:
                evidence_count = (
                    await session.execute(
                        select(func.count(FindingEvidenceLinkModel.id)).where(
                            FindingEvidenceLinkModel.finding_id.in_(finding_ids),
                        )
                    )
                ).scalar_one()

        # ── Risks count ───────────────────────────────────────────────────────
        risks_count = 0
        if assessment_ids:
            risks_count = (
                await session.execute(
                    select(func.count(RiskModel.id)).where(
                        RiskModel.assessment_id.in_(assessment_ids),
                        RiskModel.status != "Deleted",
                    )
                )
            ).scalar_one()

        # ── Audit events count ────────────────────────────────────────────────
        audit_event_count = (
            await session.execute(
                select(func.count(AuditEventModel.id)).where(
                    AuditEventModel.entity_id == supplier_id,
                    AuditEventModel.created_at >= period_from,
                    AuditEventModel.created_at <= period_to,
                )
            )
        ).scalar_one()

        # ── Current risk score (latest SupplierScoreModel) ────────────────────
        latest_score_row = (
            await session.execute(
                select(SupplierScoreModel)
                .where(SupplierScoreModel.supplier_id == supplier_id)
                .order_by(SupplierScoreModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest_score_row and latest_score_row.inputs:
            inp = latest_score_row.inputs
            score_inputs = ScoreInputs(
                total_assessments=inp.get("total_assessments", 0),
                approved_assessments=inp.get("approved_assessments", 0),
                critical_findings=inp.get("critical_findings", 0),
                high_findings=inp.get("high_findings", 0),
                medium_findings=inp.get("medium_findings", 0),
                low_findings=inp.get("low_findings", 0),
                critical_risks=inp.get("critical_risks", 0),
                high_risks=inp.get("high_risks", 0),
                medium_risks=inp.get("medium_risks", 0),
                overdue_actions=inp.get("overdue_actions", 0),
                open_actions=inp.get("open_actions", 0),
            )
            risk_score_vo = calculate(score_inputs)
            risk_score = risk_score_vo.composite_score
            risk_band = risk_score_vo.band.value
        else:
            risk_score = 0.0
            risk_band = "Low"

        # ── Active prompt versions ────────────────────────────────────────────
        registry = PromptRegistry(session)
        active_prompt_names: list[str] = []
        for name in _TRACKED_PROMPTS:
            pv = await registry.get_active(name)
            if pv:
                active_prompt_names.append(f"{name}@v{pv.version}")

        methodology = MethodologySnapshot(
            formula_version=FORMULA_VERSION,
            extraction_model=self._extraction_model,
            main_model=self._main_model,
            active_prompt_names=tuple(active_prompt_names),
        )

        return AuditPackage(
            package_id=str(uuid.uuid4()),
            supplier_id=supplier_id,
            period_from=period_from,
            period_to=period_to,
            generated_at=datetime.now(UTC),
            generator_version=_GENERATOR_VERSION,
            methodology=methodology,
            assessment_ids=assessment_ids,
            findings_count=findings_count,
            risks_count=risks_count,
            evidence_count=evidence_count,
            audit_event_count=audit_event_count,
            risk_score=risk_score,
            risk_band=risk_band,
        )
