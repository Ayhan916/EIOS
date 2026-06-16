"""
FastAPI dependency injection for EIOS API.

Each dependency provides a repository scoped to the request's database transaction.
The transaction commits at request end (on success) and rolls back on exception.
"""

from collections.abc import AsyncGenerator
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import UserRole, has_min_role
from domain.user import User
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.repositories import (
    SQLAgentRunRepository,
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLEvidenceRepository,
    SQLFindingRepository,
    SQLOrganizationRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLSectorRepository,
    SQLUserRepository,
    SQLWorkflowJobRepository,
    SQLWorkflowRunRepository,
)
from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository
from infrastructure.persistence.repositories.report import SQLReportRepository
from shared.security import decode_token

_bearer = HTTPBearer(auto_error=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


async def get_assessment_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAssessmentRepository:
    return SQLAssessmentRepository(session)


async def get_sector_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLSectorRepository:
    return SQLSectorRepository(session)


async def get_finding_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLFindingRepository:
    return SQLFindingRepository(session)


async def get_risk_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLRiskRepository:
    return SQLRiskRepository(session)


async def get_evidence_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLEvidenceRepository:
    return SQLEvidenceRepository(session)


async def get_recommendation_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLRecommendationRepository:
    return SQLRecommendationRepository(session)


async def get_user_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLUserRepository:
    return SQLUserRepository(session)


async def get_agent_run_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAgentRunRepository:
    return SQLAgentRunRepository(session)


async def get_workflow_run_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWorkflowRunRepository:
    return SQLWorkflowRunRepository(session)


async def get_audit_event_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAuditEventRepository:
    return SQLAuditEventRepository(session)


async def get_workflow_job_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLWorkflowJobRepository:
    return SQLWorkflowJobRepository(session)


async def get_organization_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLOrganizationRepository:
    return SQLOrganizationRepository(session)


async def get_chunk_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLEvidenceChunkRepository:
    return SQLEvidenceChunkRepository(session)


async def get_report_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLReportRepository:
    return SQLReportRepository(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    repo: SQLUserRepository = Depends(get_user_repo),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(min_role: UserRole) -> Callable:
    """Return a FastAPI dependency that enforces a minimum role."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not has_min_role(current_user.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{min_role.value}' or higher is required",
            )
        return current_user
    return _check


require_analyst: Callable = require_role(UserRole.ANALYST)
require_reviewer: Callable = require_role(UserRole.REVIEWER)
require_admin: Callable = require_role(UserRole.ADMIN)
