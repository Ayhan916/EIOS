from sqlalchemy import Column, DateTime, String, Text

from infrastructure.persistence.models.base import BaseModel


class ProductionChecklistItemModel(BaseModel):
    __tablename__ = "production_checklist_items"

    organization_id = Column(String(36), nullable=False, index=True)
    category = Column(
        String(50), nullable=False
    )  # Infrastructure/Security/Data/Operations/Compliance/Testing
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="Pending")  # Pending/Complete/N/A
    priority = Column(String(20), nullable=False, default="HIGH")  # HIGH/MEDIUM/LOW
    owner = Column(String(255), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
