from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class RegulationModel(BaseModel):
    __tablename__ = "regulations"
    __table_args__ = (Index("ix_regulations_code", "code", unique=True),)

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, default="Global")
    reg_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reg_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class RegulationRequirementModel(BaseModel):
    __tablename__ = "regulation_requirements"
    __table_args__ = (
        Index("ix_regulation_requirements_code", "code", unique=True),
        Index("ix_regulation_requirements_regulation", "regulation_id"),
    )

    regulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    pillar: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    obligation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="mandatory")
    keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class RequirementMappingModel(BaseModel):
    __tablename__ = "requirement_mappings"
    __table_args__ = (
        Index("ix_req_mappings_org", "organization_id"),
        Index("ix_req_mappings_entity", "entity_type", "entity_id"),
        Index("ix_req_mappings_requirement", "regulation_requirement_id"),
        UniqueConstraint(
            "organization_id",
            "regulation_requirement_id",
            "entity_type",
            "entity_id",
            name="uq_req_mappings_entity_requirement",
        ),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    regulation_requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulation_requirements.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mapping_method: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    mapping_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    regulation_version_at_mapping: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0"
    )
    mapped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assessment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ComplianceGapModel(BaseModel):
    __tablename__ = "compliance_gaps"
    __table_args__ = (
        Index("ix_compliance_gaps_org", "organization_id"),
        Index("ix_compliance_gaps_requirement", "regulation_requirement_id"),
        Index("ix_compliance_gaps_supplier", "supplier_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    regulation_requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulation_requirements.id"), nullable=False
    )
    supplier_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    gap_type: Mapped[str] = mapped_column(String(50), nullable=False, default="missing_evidence")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    regulation_version_at_calculation: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0"
    )
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ComplianceReportModel(BaseModel):
    """Immutable snapshot of a generated compliance report.

    report_data stores the full framework + gap state captured at generation
    time. PDFs are rendered from this snapshot on every download, never from
    live DB state.
    """

    __tablename__ = "compliance_reports"
    __table_args__ = (Index("ix_compliance_reports_org_type", "organization_id", "report_type"),)

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    framework_code: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    framework_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class ProductComplianceScanModel(BaseModel):
    """Timestamped BOM-level compliance scan for a product against one regulation.

    Scanned by comparing each BOM material's MaterialComplianceFlagModel entry.
    scan_result: COMPLIANT | NON_COMPLIANT | PARTIAL | UNKNOWN
    """

    __tablename__ = "product_compliance_scans"
    __table_args__ = (
        Index("ix_pcs_org", "organization_id"),
        Index("ix_pcs_product", "product_id"),
        Index("ix_pcs_regulation", "regulation_code"),
        Index("ix_pcs_result", "scan_result"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    regulation_code: Mapped[str] = mapped_column(String(50), nullable=False)
    scan_result: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    total_materials: Mapped[int] = mapped_column(nullable=False, default=0)
    compliant_count: Mapped[int] = mapped_column(nullable=False, default=0)
    non_compliant_count: Mapped[int] = mapped_column(nullable=False, default=0)
    unknown_count: Mapped[int] = mapped_column(nullable=False, default=0)
    flagged_material_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scan_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scanned_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
