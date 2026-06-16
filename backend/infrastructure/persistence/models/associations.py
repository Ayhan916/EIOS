"""
EIOS M:N Association Tables

All many-to-many join tables for the EIOS schema.
Defined here to avoid circular imports between model files.
"""

from sqlalchemy import Column, ForeignKey, String, Table

from .base import Base

assessment_evidence = Table(
    "assessment_evidence",
    Base.metadata,
    Column("assessment_id", String(36), ForeignKey("assessments.id"), primary_key=True),
    Column("evidence_id", String(36), ForeignKey("evidences.id"), primary_key=True),
)

finding_evidence = Table(
    "finding_evidence",
    Base.metadata,
    Column("finding_id", String(36), ForeignKey("findings.id"), primary_key=True),
    Column("evidence_id", String(36), ForeignKey("evidences.id"), primary_key=True),
)

risk_finding = Table(
    "risk_finding",
    Base.metadata,
    Column("risk_id", String(36), ForeignKey("risks.id"), primary_key=True),
    Column("finding_id", String(36), ForeignKey("findings.id"), primary_key=True),
)

recommendation_risk = Table(
    "recommendation_risk",
    Base.metadata,
    Column("recommendation_id", String(36), ForeignKey("recommendations.id"), primary_key=True),
    Column("risk_id", String(36), ForeignKey("risks.id"), primary_key=True),
)

recommendation_finding = Table(
    "recommendation_finding",
    Base.metadata,
    Column("recommendation_id", String(36), ForeignKey("recommendations.id"), primary_key=True),
    Column("finding_id", String(36), ForeignKey("findings.id"), primary_key=True),
)

control_risk = Table(
    "control_risk",
    Base.metadata,
    Column("control_id", String(36), ForeignKey("controls.id"), primary_key=True),
    Column("risk_id", String(36), ForeignKey("risks.id"), primary_key=True),
)

control_requirement = Table(
    "control_requirement",
    Base.metadata,
    Column("control_id", String(36), ForeignKey("controls.id"), primary_key=True),
    Column("requirement_id", String(36), ForeignKey("requirements.id"), primary_key=True),
)

policy_requirement = Table(
    "policy_requirement",
    Base.metadata,
    Column("policy_id", String(36), ForeignKey("policies.id"), primary_key=True),
    Column("requirement_id", String(36), ForeignKey("requirements.id"), primary_key=True),
)

policy_control = Table(
    "policy_control",
    Base.metadata,
    Column("policy_id", String(36), ForeignKey("policies.id"), primary_key=True),
    Column("control_id", String(36), ForeignKey("controls.id"), primary_key=True),
)

standard_requirement = Table(
    "standard_requirement",
    Base.metadata,
    Column("standard_id", String(36), ForeignKey("standards.id"), primary_key=True),
    Column("requirement_id", String(36), ForeignKey("requirements.id"), primary_key=True),
)

decision_recommendation = Table(
    "decision_recommendation",
    Base.metadata,
    Column("decision_id", String(36), ForeignKey("decisions.id"), primary_key=True),
    Column("recommendation_id", String(36), ForeignKey("recommendations.id"), primary_key=True),
)
