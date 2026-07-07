"""CSDDD-009 — ESAP Export API (Art. 16 Abs. 2).

GET  /esap/taxonomy              ESAP taxonomy mapping
GET  /esap/export                generate JSON or XML export (format=json|xml)
GET  /esap/validate              pre-submission validation
GET  /esap/submissions           list submissions
POST /esap/submissions           create submission record
GET  /esap/submissions/{id}      get submission
POST /esap/submissions/{id}/ready   mark ready
POST /esap/submissions/{id}/submit  record ESAP submission (manual)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from application.csddd.esap_exporter import TAXONOMY_MAPPING, build_export, to_json, to_xml
from domain.user import User
from infrastructure.persistence.repositories.esap import SQLESAPRepository
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/esap", tags=["esap-export"])


class SubmissionCreate(BaseModel):
    report_year: int = Field(ge=2024, le=2040)
    export_format: str = Field(default="json")
    notes: str = Field(default="", max_length=2000)


class SubmissionOut(BaseModel):
    id: str
    organization_id: str
    report_year: int
    export_format: str
    status: str
    submitted_at: Any | None
    submitted_by: str | None
    confirmation_reference: str | None
    notes: str
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class MarkSubmittedBody(BaseModel):
    submitted_by: str = Field(min_length=1, max_length=255)
    confirmation_reference: str = Field(min_length=1, max_length=255)


@router.get("/taxonomy")
def get_taxonomy(user: User = Depends(get_current_user)):
    """Return ESAP/XBRL taxonomy mapping for CSDDD Art. 16 fields."""
    return {
        "schema_version": "CSDDD-ESAP-2024-01",
        "note": "ESAP obligation applies from ca. 2031 per EU Regulation 2023/2859. Taxonomy subject to change until then.",
        "mapping": TAXONOMY_MAPPING,
    }


@router.get("/export")
def export_report(
    report_year: int = Query(default=2024, ge=2024, le=2040),
    fmt: str = Query(default="json", alias="format"),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """Generate a structured ESAP-ready report (JSON or XML)."""
    if fmt not in ("json", "xml"):
        raise HTTPException(status_code=422, detail="format must be 'json' or 'xml'")
    bundle = build_export(db, user.organization_id, report_year)
    if fmt == "xml":
        xml_str = to_xml(bundle)
        return Response(content=xml_str, media_type="application/xml")
    return {
        "export": to_json(bundle),
        "validation": {"is_valid": bundle.is_valid, "missing_fields": bundle.missing_fields},
    }


@router.get("/validate")
def validate_report(
    report_year: int = Query(default=2024, ge=2024, le=2040),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """Pre-submission validation: check all Art. 16 mandatory fields."""
    bundle = build_export(db, user.organization_id, report_year)
    checklist = [
        {
            "field": k,
            "xbrl_concept": v["xbrl_concept"],
            "csddd_article": v["csddd_article"],
            "mandatory": v["mandatory"],
            "status": "ok" if k not in bundle.missing_fields else "missing",
        }
        for k, v in TAXONOMY_MAPPING.items()
    ]
    return {
        "report_year": report_year,
        "is_valid": bundle.is_valid,
        "missing_count": len(bundle.missing_fields),
        "checklist": checklist,
        "esap_note": "ESAP submission is a manual process until direct API upload is available (ca. 2031).",
    }


@router.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    return SQLESAPRepository(db).list_org(user.organization_id)


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    body: SubmissionCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    if body.export_format not in ("json", "xml"):
        raise HTTPException(status_code=422, detail="export_format must be 'json' or 'xml'")
    repo = SQLESAPRepository(db)
    sub = repo.create(user.organization_id, body.report_year, body.export_format, body.notes)
    db.commit()
    return sub


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    s = SQLESAPRepository(db).get(submission_id, user.organization_id)
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    return s


@router.post("/submissions/{submission_id}/ready", response_model=SubmissionOut)
def mark_ready(
    submission_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLESAPRepository(db)
    s = repo.mark_ready(submission_id, user.organization_id)
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.commit()
    return s


@router.post("/submissions/{submission_id}/submit", response_model=SubmissionOut)
def record_submission(
    submission_id: str,
    body: MarkSubmittedBody,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """Record that the ESAP submission was made manually (no direct API yet)."""
    repo = SQLESAPRepository(db)
    s = repo.mark_submitted(
        submission_id, user.organization_id, body.submitted_by, body.confirmation_reference
    )
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    db.commit()
    return s
