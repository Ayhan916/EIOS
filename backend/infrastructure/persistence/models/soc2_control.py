from sqlalchemy import Column, String, Text, UniqueConstraint

from infrastructure.persistence.models.base import BaseModel


class Soc2ControlModel(BaseModel):
    __tablename__ = "soc2_controls"
    __table_args__ = (
        UniqueConstraint("organization_id", "control_id", name="uq_soc2_org_control"),
    )

    organization_id = Column(String(36), nullable=False, index=True)
    control_id = Column(String(20), nullable=False)  # e.g. "CC6.1"
    category = Column(String(10), nullable=False)  # CC1-CC9, A1, C1
    control_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="Not Started")
    evidence_notes = Column(Text, nullable=True)
    owner = Column(String(255), nullable=True)
