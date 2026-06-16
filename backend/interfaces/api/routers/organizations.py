from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from domain.user import User
from infrastructure.persistence.repositories import SQLOrganizationRepository
from interfaces.api.deps import get_current_user, get_organization_repo
from interfaces.api.schemas.organization import OrganizationResponse

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    org_repo: SQLOrganizationRepository = Depends(get_organization_repo),
) -> OrganizationResponse:
    """Return the organization the current user belongs to."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with any organization",
        )
    org = await org_repo.get_by_id(current_user.organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return OrganizationResponse.model_validate(org)
