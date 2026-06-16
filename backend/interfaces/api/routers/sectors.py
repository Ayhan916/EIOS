from fastapi import APIRouter, Depends, HTTPException, status

from domain.sector import Sector
from infrastructure.persistence.repositories import SQLSectorRepository
from interfaces.api.deps import get_current_user, get_sector_repo
from interfaces.api.schemas.sector import SectorCreate, SectorResponse

router = APIRouter(
    prefix="/sectors",
    tags=["sectors"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=SectorResponse, status_code=status.HTTP_201_CREATED)
async def create_sector(
    body: SectorCreate,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> SectorResponse:
    sector = Sector(
        name=body.name,
        nace_code=body.nace_code,
        nace_description=body.nace_description,
        risk_profile=body.risk_profile,
        parent_sector_id=body.parent_sector_id,
        organization_id=body.organization_id,
    )
    saved = await repo.save(sector)
    return SectorResponse.model_validate(saved)


@router.get("/{sector_id}", response_model=SectorResponse)
async def get_sector(
    sector_id: str,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> SectorResponse:
    sector = await repo.get_by_id(sector_id)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    return SectorResponse.model_validate(sector)


@router.get("/nace/{nace_code}", response_model=SectorResponse)
async def get_sector_by_nace(
    nace_code: str,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> SectorResponse:
    sector = await repo.get_by_nace_code(nace_code)
    if sector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    return SectorResponse.model_validate(sector)


@router.get("/{sector_id}/children", response_model=list[SectorResponse])
async def list_sector_children(
    sector_id: str,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> list[SectorResponse]:
    children = await repo.list_children(sector_id)
    return [SectorResponse.model_validate(s) for s in children]


@router.delete("/{sector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sector(
    sector_id: str,
    repo: SQLSectorRepository = Depends(get_sector_repo),
) -> None:
    existing = await repo.get_by_id(sector_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sector not found")
    await repo.delete(sector_id)
