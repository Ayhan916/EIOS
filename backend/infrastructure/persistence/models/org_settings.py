"""M48.2 G-055 — Organization Settings (White-Labeling)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class OrganizationSettingsModel(Base):
    """Per-organization white-labeling and branding settings.

    One row per organization. organization_id is the PK (not UUID-generated).
    """

    __tablename__ = "organization_settings"

    organization_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # White-labeling (G-055)
    company_name_override: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # "#RRGGBB"
    favicon_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Integrations (G-022 — stored encrypted or as opaque references)
    teams_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JIRA / ServiceNow (G-047)
    jira_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jira_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    jira_api_token_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)  # SecretRef
    servicenow_instance_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    servicenow_username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    servicenow_password_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # SharePoint (G-049)
    sharepoint_tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sharepoint_client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sharepoint_site_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sharepoint_refresh_token_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # LLM model settings per job (ADR-012 extension)
    llm_model_settings: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    pipeline_settings: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
