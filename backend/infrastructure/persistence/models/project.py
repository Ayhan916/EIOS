from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class ProjectModel(BaseModel):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )

    organization: Mapped[OrganizationModel | None] = relationship(back_populates="projects")
    tasks: Mapped[list[TaskModel]] = relationship(back_populates="project")
