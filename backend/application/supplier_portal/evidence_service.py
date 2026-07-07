"""M35 Evidence Request & Submission Service.

Manages the full evidence workflow:
  Internal:
    create_evidence_request()     — internal user creates a request
    list_evidence_requests()      — list by supplier + org
    review_submission()           — accept / reject / request revision
  Supplier:
    get_my_evidence_requests()    — supplier sees only their own requests
    create_submission()           — supplier creates a draft submission
    attach_file()                 — add a file to a submission
    submit_evidence()             — submit a draft for review

Isolation: all queries are scoped by both supplier_id and organization_id.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def _log_activity(
    supplier_id: str,
    supplier_user_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    session,
    metadata: dict | None = None,
) -> None:
    import json

    from infrastructure.persistence.models.supplier_portal import SupplierActivityEventModel

    now = datetime.now(UTC)
    model = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}),
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("evidence_activity_log_failed", error=str(exc))


async def create_evidence_request(
    supplier_id: str,
    organization_id: str,
    title: str,
    description: str,
    created_by_user_id: str,
    due_date: datetime | None = None,
    assessment_id: str | None = None,
    assigned_to_supplier_user_id: str | None = None,
    session=None,
) -> object:
    from infrastructure.persistence.models.supplier_portal import EvidenceRequestModel

    now = datetime.now(UTC)
    model = EvidenceRequestModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        organization_id=organization_id,
        assessment_id=assessment_id,
        title=title,
        description=description,
        due_date=due_date,
        evidence_status="open",
        created_by_user_id=created_by_user_id,
        assigned_to_supplier_user_id=assigned_to_supplier_user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()
    logger.info("evidence_request_created", request_id=model.id, supplier_id=supplier_id)
    return model


async def list_evidence_requests(
    supplier_id: str,
    organization_id: str,
    status: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import EvidenceRequestModel

    stmt = select(EvidenceRequestModel).where(
        EvidenceRequestModel.supplier_id == supplier_id,
        EvidenceRequestModel.organization_id == organization_id,
    )
    if status:
        stmt = stmt.where(EvidenceRequestModel.evidence_status == status)
    stmt = stmt.order_by(EvidenceRequestModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_evidence_request(
    request_id: str,
    organization_id: str,
    session=None,
) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import EvidenceRequestModel

    stmt = select(EvidenceRequestModel).where(
        EvidenceRequestModel.id == request_id,
        EvidenceRequestModel.organization_id == organization_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_supplier_evidence_request(
    request_id: str,
    supplier_id: str,
    session=None,
) -> object | None:
    """Load an evidence request scoped to the calling supplier."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import EvidenceRequestModel

    stmt = select(EvidenceRequestModel).where(
        EvidenceRequestModel.id == request_id,
        EvidenceRequestModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_submission(
    evidence_request_id: str,
    supplier_user_id: str,
    supplier_id: str,
    comments: str = "",
    session=None,
) -> object:
    """F8: return existing draft if one exists; reject if already submitted/reviewed."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import EvidenceSubmissionModel

    existing_stmt = select(EvidenceSubmissionModel).where(
        EvidenceSubmissionModel.evidence_request_id == evidence_request_id,
        EvidenceSubmissionModel.supplier_id == supplier_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        if existing.submission_status == "draft":
            return existing
        raise ValueError(
            f"A submission already exists for this request with status '{existing.submission_status}'"
        )

    now = datetime.now(UTC)
    model = EvidenceSubmissionModel(
        id=str(uuid.uuid4()),
        evidence_request_id=evidence_request_id,
        supplier_user_id=supplier_user_id,
        supplier_id=supplier_id,
        comments=comments,
        submission_status="draft",
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()
    return model


async def attach_file_to_submission(
    submission_id: str,
    supplier_id: str,
    file_name: str,
    file_path: str,
    file_size: int,
    content_type: str,
    session=None,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import (
        EvidenceSubmissionFileModel,
        EvidenceSubmissionModel,
    )

    # Verify submission belongs to this supplier
    stmt = select(EvidenceSubmissionModel).where(
        EvidenceSubmissionModel.id == submission_id,
        EvidenceSubmissionModel.supplier_id == supplier_id,
    )
    sub = (await session.execute(stmt)).scalar_one_or_none()
    if sub is None:
        raise ValueError("Submission not found or does not belong to this supplier")
    if sub.submission_status != "draft":
        raise ValueError("Cannot add files to a submitted or reviewed submission")

    now = datetime.now(UTC)
    file_model = EvidenceSubmissionFileModel(
        id=str(uuid.uuid4()),
        submission_id=submission_id,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        content_type=content_type,
        uploaded_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(file_model)
    await session.flush()
    return file_model


async def submit_evidence(
    submission_id: str,
    supplier_id: str,
    supplier_user_id: str | None = None,
    session=None,
) -> object:
    """Transition a draft submission to 'submitted'. F5: logs activity event."""
    from sqlalchemy import select, update

    from infrastructure.persistence.models.supplier_portal import (
        EvidenceRequestModel,
        EvidenceSubmissionModel,
    )

    stmt = select(EvidenceSubmissionModel).where(
        EvidenceSubmissionModel.id == submission_id,
        EvidenceSubmissionModel.supplier_id == supplier_id,
    )
    sub = (await session.execute(stmt)).scalar_one_or_none()
    if sub is None:
        raise ValueError("Submission not found")
    if sub.submission_status != "draft":
        raise ValueError(f"Cannot submit a submission in status: {sub.submission_status}")

    now = datetime.now(UTC)
    sub.submission_status = "submitted"
    sub.submitted_at = now
    sub.updated_at = now

    # Advance the parent request to in_progress
    req_stmt = (
        update(EvidenceRequestModel)
        .where(
            EvidenceRequestModel.id == sub.evidence_request_id,
            EvidenceRequestModel.evidence_status == "open",
        )
        .values(evidence_status="in_progress", updated_at=now)
    )
    await session.execute(req_stmt)
    await session.flush()

    # F5: activity audit
    await _log_activity(
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id or sub.supplier_user_id,
        event_type="evidence_submitted",
        entity_type="evidence_submission",
        entity_id=submission_id,
        session=session,
    )
    return sub


async def review_submission(
    submission_id: str,
    organization_id: str,
    reviewed_by: str,
    new_status: str,
    reviewer_comments: str = "",
    session=None,
) -> object:
    """Internal reviewer accepts, rejects, or requests revision on a submission."""
    from sqlalchemy import select, update

    from infrastructure.persistence.models.supplier_portal import (
        EvidenceRequestModel,
        EvidenceSubmissionModel,
    )

    _VALID = {"accepted", "rejected", "revision_requested"}
    if new_status not in _VALID:
        raise ValueError(f"Invalid review status: {new_status}. Must be one of {_VALID}")

    # F3: SELECT FOR UPDATE to serialize concurrent reviewers
    stmt = (
        select(EvidenceSubmissionModel)
        .join(
            EvidenceRequestModel,
            EvidenceSubmissionModel.evidence_request_id == EvidenceRequestModel.id,
        )
        .where(
            EvidenceSubmissionModel.id == submission_id,
            EvidenceRequestModel.organization_id == organization_id,
        )
        .with_for_update()
    )
    sub = (await session.execute(stmt)).scalar_one_or_none()
    if sub is None:
        raise ValueError("Submission not found or not in your organisation")
    if sub.submission_status != "submitted":
        raise ValueError(f"Cannot review a submission in status: {sub.submission_status}")

    now = datetime.now(UTC)
    sub.submission_status = new_status
    sub.reviewed_by = reviewed_by
    sub.reviewed_at = now
    sub.reviewer_comments = reviewer_comments
    sub.updated_at = now

    # Propagate accepted/rejected to the parent request
    request_status = {
        "accepted": "accepted",
        "rejected": "rejected",
        "revision_requested": "in_progress",
    }[new_status]

    req_update = (
        update(EvidenceRequestModel)
        .where(EvidenceRequestModel.id == sub.evidence_request_id)
        .values(evidence_status=request_status, updated_at=now)
    )
    await session.execute(req_update)
    await session.flush()

    # F5: activity audit
    await _log_activity(
        supplier_id=sub.supplier_id,
        supplier_user_id=None,
        event_type=f"evidence_{new_status}",
        entity_type="evidence_submission",
        entity_id=submission_id,
        metadata={"reviewed_by": reviewed_by},
        session=session,
    )
    return sub
