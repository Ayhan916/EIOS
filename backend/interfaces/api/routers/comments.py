"""
M26 Comments API

Supports polymorphic comments on Assessment, Finding, Risk, Recommendation.
Each comment is auditable, soft-deletable, and supports @mention notifications.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_events
from application.collaboration.mentions import notify_mentions, resolve_mentions
from domain.comment import Comment
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLCommentRepository,
    SQLFindingRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLUserRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_comment_repo,
    get_current_user,
    get_db,
    get_finding_repo,
    get_recommendation_repo,
    get_risk_repo,
    get_user_repo,
    require_analyst,
)
from interfaces.api.schemas.comment import CommentCreate, CommentEdit, CommentResponse

logger = structlog.get_logger(__name__)

_ALLOWED_ENTITY_TYPES = frozenset({"Assessment", "Finding", "Risk", "Recommendation"})


async def _resolve_entity_org_id(
    entity_type: str,
    entity_id: str,
    assessment_repo: SQLAssessmentRepository,
    finding_repo: SQLFindingRepository,
    risk_repo: SQLRiskRepository,
    recommendation_repo: SQLRecommendationRepository,
) -> str | None:
    """Return the organization_id of the entity that owns these comments, or None if not found."""
    if entity_type == "Assessment":
        obj = await assessment_repo.get_by_id(entity_id)
        return obj.organization_id if obj else None

    if entity_type == "Finding":
        obj = await finding_repo.get_by_id(entity_id)
        if obj and obj.assessment_id:
            parent = await assessment_repo.get_by_id(obj.assessment_id)
            return parent.organization_id if parent else None
        return None

    if entity_type == "Risk":
        obj = await risk_repo.get_by_id(entity_id)
        if obj and obj.assessment_id:
            parent = await assessment_repo.get_by_id(obj.assessment_id)
            return parent.organization_id if parent else None
        return None

    if entity_type == "Recommendation":
        obj = await recommendation_repo.get_by_id(entity_id)
        if obj and obj.assessment_id:
            parent = await assessment_repo.get_by_id(obj.assessment_id)
            return parent.organization_id if parent else None
        return None

    return None


router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    dependencies=[Depends(get_current_user)],
)


def _to_response(comment: Comment, author_name: str | None = None) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        entity_type=comment.entity_type,
        entity_id=comment.entity_id,
        author_id=comment.author_id,
        author_name=author_name,
        content=comment.content if not comment.is_deleted else "[deleted]",
        edited_at=comment.edited_at,
        deleted_at=comment.deleted_at,
        mentioned_user_ids=comment.mentioned_user_ids,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        is_deleted=comment.is_deleted,
        is_edited=comment.is_edited,
    )


@router.post(
    "/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_comment(
    body: CommentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    comment_repo: SQLCommentRepository = Depends(get_comment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> CommentResponse:
    if body.entity_type not in _ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"entity_type must be one of {sorted(_ALLOWED_ENTITY_TYPES)}",
        )

    # Resolve @mentions before persisting
    mentioned_ids = await resolve_mentions(
        content=body.content,
        organization_id=current_user.organization_id or "",
        session=session,
    )

    comment = Comment(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        author_id=current_user.id,
        content=body.content,
        mentioned_user_ids=mentioned_ids,
        status=EntityStatus.ACTIVE,
        created_by=current_user.id,
    )
    saved = await comment_repo.save(comment)

    await audit_repo.save(
        audit_events.comment_created(
            comment_id=saved.id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            author_id=current_user.id,
            author_email=current_user.email,
        )
    )

    # Fire mention notifications (best-effort; does not affect response)
    await notify_mentions(
        session=session,
        mentioned_user_ids=mentioned_ids,
        author_name=current_user.display_name,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        assessment_id=body.entity_id,
        organization_id=current_user.organization_id or "",
    )

    logger.info("comment_created", comment_id=saved.id, entity_type=body.entity_type)
    return _to_response(saved, current_user.display_name)


@router.get("/", response_model=list[CommentResponse])
async def list_comments(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    include_deleted: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    comment_repo: SQLCommentRepository = Depends(get_comment_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    finding_repo: SQLFindingRepository = Depends(get_finding_repo),
    risk_repo: SQLRiskRepository = Depends(get_risk_repo),
    recommendation_repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> list[CommentResponse]:
    if entity_type not in _ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"entity_type must be one of {sorted(_ALLOWED_ENTITY_TYPES)}",
        )

    # Tenant isolation: verify caller belongs to the same org as the parent entity
    entity_org_id = await _resolve_entity_org_id(
        entity_type,
        entity_id,
        assessment_repo,
        finding_repo,
        risk_repo,
        recommendation_repo,
    )
    if entity_org_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    if entity_org_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    comments = await comment_repo.list_by_entity(entity_type, entity_id, include_deleted)

    # Batch-load author names
    author_ids = list({c.author_id for c in comments})
    authors: dict[str, str] = {}
    for uid in author_ids:
        u = await user_repo.get_by_id(uid)
        if u:
            authors[uid] = u.display_name

    return [_to_response(c, authors.get(c.author_id)) for c in comments]


@router.patch("/{comment_id}", response_model=CommentResponse)
async def edit_comment(
    comment_id: str,
    body: CommentEdit,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    comment_repo: SQLCommentRepository = Depends(get_comment_repo),
) -> CommentResponse:
    comment = await comment_repo.get_by_id(comment_id)
    if comment is None or comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can edit a comment"
        )

    comment.content = body.content
    comment.edited_at = datetime.now(UTC)
    comment.updated_by = current_user.id
    saved = await comment_repo.save(comment)
    return _to_response(saved, current_user.display_name)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    comment_repo: SQLCommentRepository = Depends(get_comment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> None:
    comment = await comment_repo.get_by_id(comment_id)
    if comment is None or comment.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    # Admins can delete any comment; authors can delete their own
    from domain.enums import UserRole, has_min_role

    is_admin = has_min_role(current_user.role, UserRole.ADMIN)
    if not is_admin and comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's comment"
        )

    comment.deleted_at = datetime.now(UTC)
    comment.updated_by = current_user.id
    await comment_repo.save(comment)

    await audit_repo.save(
        audit_events.comment_deleted(
            comment_id=comment_id,
            entity_type=comment.entity_type,
            entity_id=comment.entity_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    )
