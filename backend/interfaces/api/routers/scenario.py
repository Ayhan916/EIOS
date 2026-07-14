"""Proactive Scenario Intelligence API.

Endpoints:
  POST /scenario/analyze           — Vollständige Szenario-Analyse
  GET  /scenario/sector-suppliers  — Lieferanten in einem Sektor
  GET  /scenario/detect-sector     — Sektor aus Signal-Text erkennen
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.intelligence.scenario_analyzer import (
    detect_sector,
    find_suppliers_in_sector,
    run_scenario_analysis,
)
from application.ports.llm import LLMProvider
from domain.user import User
from infrastructure.llm.deps import get_llm_provider
from interfaces.api.deps import get_current_user, get_db

router = APIRouter(prefix="/scenario", tags=["Scenario Intelligence"])


class ScenarioRequest(BaseModel):
    signal_text: str = Field(..., min_length=10, max_length=2000,
                             description="Der Nachrichtentext / das Ereignis")
    company_name: str = Field(..., min_length=2, max_length=200,
                              description="Das betroffene Unternehmen (z.B. 'Volkswagen')")
    sector: str = Field(..., min_length=2, max_length=100,
                        description="Die Branche (z.B. 'automotive')")


@router.post("/analyze")
async def analyze_scenario(
    body: ScenarioRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> dict:
    """Projiziert ein externes Ereignis auf das Lieferanten-Portfolio."""
    return await run_scenario_analysis(
        signal_text=body.signal_text,
        company_name=body.company_name,
        sector=body.sector,
        org_id=current_user.organization_id,
        session=session,
        llm=llm,
    )


@router.get("/sector-suppliers")
async def sector_suppliers(
    sector: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Lieferanten im angegebenen Sektor."""
    suppliers = await find_suppliers_in_sector(sector, current_user.organization_id, session)
    return {"sector": sector, "count": len(suppliers), "suppliers": suppliers}


@router.get("/detect-sector")
async def detect_sector_from_text(
    text: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Erkennt den Sektor aus einem Signal-Text."""
    sector = detect_sector(text)
    return {"sector": sector, "detected": sector is not None}
