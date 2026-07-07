"""CSDDD-010 — Threshold Monitor API (Art. 2).

GET  /threshold/status           current threshold status (deterministic)
GET  /threshold/profiles         list company profiles (history)
POST /threshold/profiles         upsert company profile for a fiscal year
GET  /threshold/info             static info about CSDDD thresholds + deadlines
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from application.compliance.threshold_calculator import calculate
from domain.user import User
from infrastructure.persistence.repositories.threshold_monitor import SQLCompanyProfileRepository
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/threshold", tags=["threshold-monitor"])

_STATIC_INFO = {
    "tier_1": {
        "employees": 5000,
        "revenue_eur_millions": 1500,
        "deadline": "2027-07-26",
        "obligations": [
            "Art. 7 DD Policy",
            "Art. 10 Prevention",
            "Art. 11 Remediation",
            "Art. 13 Stakeholder",
            "Art. 14 Grievance",
            "Art. 16 Annual Report",
            "Art. 22 Board Oversight",
        ],
    },
    "tier_2": {
        "employees": 1000,
        "revenue_eur_millions": 450,
        "deadline": "2028-07-26",
        "obligations": [
            "Art. 7 DD Policy",
            "Art. 10 Prevention",
            "Art. 14 Grievance",
            "Art. 16 Annual Report",
        ],
    },
    "borderline_pct": 20,
    "source": "EU Directive 2024/1760 (CSDDD), Art. 2",
}


class ProfileUpsert(BaseModel):
    fiscal_year: int = Field(ge=2020, le=2040)
    employee_count_worldwide: int = Field(ge=0)
    net_revenue_eur_millions: float = Field(ge=0)
    headquarters_country: str = Field(default="DE", max_length=2)
    sector: str = Field(default="", max_length=100)
    non_eu_company: bool = Field(default=False)
    notes: str = Field(default="", max_length=2000)


class ProfileOut(BaseModel):
    id: str
    organization_id: str
    fiscal_year: int
    employee_count_worldwide: int
    net_revenue_eur_millions: float
    headquarters_country: str
    sector: str
    non_eu_company: bool
    notes: str
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


@router.get("/info")
def threshold_info(user: User = Depends(get_current_user)):
    """Static CSDDD threshold reference information."""
    return _STATIC_INFO


@router.get("/status")
def get_status(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """Deterministic threshold status based on latest company profile."""
    repo = SQLCompanyProfileRepository(db)
    profile = repo.latest(user.organization_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No company profile found. Please add your company profile first via POST /threshold/profiles.",
        )
    result = calculate(profile)
    return {
        "fiscal_year": result.fiscal_year,
        "level": result.level,
        "employee_count": result.employee_count,
        "net_revenue_eur_millions": result.net_revenue_eur_millions,
        "tier1": {
            "employee_met": result.tier1_employee_met,
            "revenue_met": result.tier1_revenue_met,
            "deadline": result.tier1_deadline,
        },
        "tier2": {
            "employee_met": result.tier2_employee_met,
            "revenue_met": result.tier2_revenue_met,
            "deadline": result.tier2_deadline,
        },
        "is_borderline": result.is_borderline,
        "borderline_message": result.borderline_message,
        "recommendation": result.recommendation,
    }


@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    return SQLCompanyProfileRepository(db).list_org(user.organization_id)


@router.post("/profiles", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def upsert_profile(
    body: ProfileUpsert,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLCompanyProfileRepository(db)
    p = repo.upsert(
        organization_id=user.organization_id,
        fiscal_year=body.fiscal_year,
        employee_count_worldwide=body.employee_count_worldwide,
        net_revenue_eur_millions=body.net_revenue_eur_millions,
        headquarters_country=body.headquarters_country.upper()[:2],
        sector=body.sector,
        non_eu_company=body.non_eu_company,
        notes=body.notes,
        created_by=str(user.email or user.id),
    )
    db.commit()
    return p
