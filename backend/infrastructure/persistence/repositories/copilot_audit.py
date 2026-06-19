"""Repositories for M33.2 Copilot Audit entities."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.copilot_audit import (
    CopilotAnswerReview,
    CopilotAuditPackage,
    CopilotCitationIntegrity,
    CopilotFeedback,
    DetectedContradiction,
)
from domain.enums import AuditVerificationStatus, EntityStatus
from infrastructure.persistence.models.copilot_audit import (
    CopilotAnswerReviewModel,
    CopilotAuditPackageModel,
    CopilotCitationIntegrityModel,
    CopilotContradictionModel as DetectedContradictionModel,
    CopilotFeedbackModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


# ---------------------------------------------------------------------------
# Contradiction
# ---------------------------------------------------------------------------

class SQLDetectedContradictionRepository(
    BaseRepository[DetectedContradiction, DetectedContradictionModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DetectedContradictionModel)

    def _to_model(self, entity: DetectedContradiction) -> DetectedContradictionModel:
        return DetectedContradictionModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            message_id=entity.message_id,
            organization_id=entity.organization_id,
            contradiction_type=entity.contradiction_type,
            description=entity.description,
            involved_objects=entity.involved_objects,
            severity=entity.severity,
            detected_at=entity.detected_at,
        )

    def _to_domain(self, model: DetectedContradictionModel) -> DetectedContradiction:
        return DetectedContradiction(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            message_id=model.message_id,
            organization_id=model.organization_id,
            contradiction_type=model.contradiction_type,
            description=model.description,
            involved_objects=list(model.involved_objects or []),
            severity=model.severity or "warning",
            detected_at=model.detected_at or datetime.now(UTC),
        )

    async def list_for_message(
        self, message_id: str, org_id: str
    ) -> list[DetectedContradiction]:
        stmt = (
            select(DetectedContradictionModel)
            .where(
                DetectedContradictionModel.message_id == message_id,
                DetectedContradictionModel.organization_id == org_id,
            )
            .order_by(DetectedContradictionModel.detected_at.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]


# ---------------------------------------------------------------------------
# Citation Integrity
# ---------------------------------------------------------------------------

class SQLCopilotCitationIntegrityRepository(
    BaseRepository[CopilotCitationIntegrity, CopilotCitationIntegrityModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotCitationIntegrityModel)

    def _to_model(self, entity: CopilotCitationIntegrity) -> CopilotCitationIntegrityModel:
        return CopilotCitationIntegrityModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            message_id=entity.message_id,
            organization_id=entity.organization_id,
            citation_type=entity.citation_type,
            object_id=entity.object_id,
            integrity_status=entity.integrity_status
            if isinstance(entity.integrity_status, str)
            else entity.integrity_status.value,
            citation_hash=entity.citation_hash,
            citation_snapshot=entity.citation_snapshot,
            verified_at=entity.verified_at,
        )

    def _to_domain(self, model: CopilotCitationIntegrityModel) -> CopilotCitationIntegrity:
        return CopilotCitationIntegrity(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            message_id=model.message_id,
            organization_id=model.organization_id,
            citation_type=model.citation_type,
            object_id=model.object_id,
            integrity_status=model.integrity_status,
            citation_hash=model.citation_hash or "",
            citation_snapshot=dict(model.citation_snapshot or {}),
            verified_at=model.verified_at or datetime.now(UTC),
        )

    async def list_for_message(
        self, message_id: str, org_id: str
    ) -> list[CopilotCitationIntegrity]:
        stmt = (
            select(CopilotCitationIntegrityModel)
            .where(
                CopilotCitationIntegrityModel.message_id == message_id,
                CopilotCitationIntegrityModel.organization_id == org_id,
            )
            .order_by(CopilotCitationIntegrityModel.citation_type.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class SQLCopilotFeedbackRepository(
    BaseRepository[CopilotFeedback, CopilotFeedbackModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotFeedbackModel)

    def _to_model(self, entity: CopilotFeedback) -> CopilotFeedbackModel:
        return CopilotFeedbackModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            message_id=entity.message_id,
            conversation_id=entity.conversation_id,
            organization_id=entity.organization_id,
            user_id=entity.user_id,
            rating=entity.rating if isinstance(entity.rating, str) else entity.rating.value,
            reason=entity.reason,
            submitted_at=entity.submitted_at,
        )

    def _to_domain(self, model: CopilotFeedbackModel) -> CopilotFeedback:
        return CopilotFeedback(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            message_id=model.message_id,
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            user_id=model.user_id,
            rating=model.rating,
            reason=model.reason or "",
            submitted_at=model.submitted_at or datetime.now(UTC),
        )

    async def get_for_message(
        self, message_id: str, org_id: str
    ) -> CopilotFeedback | None:
        stmt = select(CopilotFeedbackModel).where(
            CopilotFeedbackModel.message_id == message_id,
            CopilotFeedbackModel.organization_id == org_id,
        ).limit(1)
        row = (await self._session.execute(stmt)).scalars().first()
        return self._to_domain(row) if row else None


# ---------------------------------------------------------------------------
# Answer Review
# ---------------------------------------------------------------------------

class SQLCopilotAnswerReviewRepository(
    BaseRepository[CopilotAnswerReview, CopilotAnswerReviewModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotAnswerReviewModel)

    def _to_model(self, entity: CopilotAnswerReview) -> CopilotAnswerReviewModel:
        return CopilotAnswerReviewModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            message_id=entity.message_id,
            conversation_id=entity.conversation_id,
            organization_id=entity.organization_id,
            reviewer_id=entity.reviewer_id,
            decision=entity.decision if isinstance(entity.decision, str) else entity.decision.value,
            notes=entity.notes,
            reviewed_at=entity.reviewed_at,
        )

    def _to_domain(self, model: CopilotAnswerReviewModel) -> CopilotAnswerReview:
        return CopilotAnswerReview(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            message_id=model.message_id,
            conversation_id=model.conversation_id,
            organization_id=model.organization_id,
            reviewer_id=model.reviewer_id,
            decision=model.decision,
            notes=model.notes or "",
            reviewed_at=model.reviewed_at or datetime.now(UTC),
        )

    async def get_for_message(
        self, message_id: str, org_id: str
    ) -> CopilotAnswerReview | None:
        stmt = select(CopilotAnswerReviewModel).where(
            CopilotAnswerReviewModel.message_id == message_id,
            CopilotAnswerReviewModel.organization_id == org_id,
        ).limit(1)
        row = (await self._session.execute(stmt)).scalars().first()
        return self._to_domain(row) if row else None


# ---------------------------------------------------------------------------
# Audit Package
# ---------------------------------------------------------------------------

class SQLCopilotAuditPackageRepository(
    BaseRepository[CopilotAuditPackage, CopilotAuditPackageModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CopilotAuditPackageModel)

    def _to_model(self, entity: CopilotAuditPackage) -> CopilotAuditPackageModel:
        return CopilotAuditPackageModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            message_id=entity.message_id,
            organization_id=entity.organization_id,
            package_hash=entity.package_hash,
            json_payload=entity.json_payload,
            generated_at=entity.generated_at,
            verification_status=entity.verification_status
            if isinstance(entity.verification_status, str)
            else entity.verification_status.value,
            verified_at=entity.verified_at,
        )

    def _to_domain(self, model: CopilotAuditPackageModel) -> CopilotAuditPackage:
        return CopilotAuditPackage(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            message_id=model.message_id,
            organization_id=model.organization_id,
            package_hash=model.package_hash,
            json_payload=dict(model.json_payload or {}),
            generated_at=model.generated_at or datetime.now(UTC),
            verification_status=model.verification_status or AuditVerificationStatus.PENDING,
            verified_at=model.verified_at,
        )

    async def get_for_message(
        self, message_id: str, org_id: str
    ) -> CopilotAuditPackage | None:
        stmt = select(CopilotAuditPackageModel).where(
            CopilotAuditPackageModel.message_id == message_id,
            CopilotAuditPackageModel.organization_id == org_id,
        ).limit(1)
        row = (await self._session.execute(stmt)).scalars().first()
        return self._to_domain(row) if row else None


# Re-export so reproducibility_verifier can import from here cleanly
from infrastructure.persistence.repositories.copilot import SQLCopilotMessageRepository  # noqa: E402
