"""M48.2 — Commercial Readiness: org_settings, custom_roles, board_access_tokens.

Revision: 062
Down revision: 061
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # G-055: White-labeling org settings
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", sa.String(36), primary_key=True),
        sa.Column("company_name_override", sa.String(200), nullable=True),
        sa.Column("logo_url", sa.String(2000), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("favicon_url", sa.String(2000), nullable=True),
        sa.Column("teams_webhook_url", sa.Text, nullable=True),
        sa.Column("slack_webhook_url", sa.Text, nullable=True),
        sa.Column("jira_base_url", sa.String(500), nullable=True),
        sa.Column("jira_email", sa.String(254), nullable=True),
        sa.Column("jira_api_token_ref", sa.String(200), nullable=True),
        sa.Column("servicenow_instance_url", sa.String(500), nullable=True),
        sa.Column("servicenow_username", sa.String(200), nullable=True),
        sa.Column("servicenow_password_ref", sa.String(200), nullable=True),
        sa.Column("sharepoint_tenant_id", sa.String(36), nullable=True),
        sa.Column("sharepoint_client_id", sa.String(36), nullable=True),
        sa.Column("sharepoint_site_id", sa.String(200), nullable=True),
        sa.Column("sharepoint_refresh_token_ref", sa.String(200), nullable=True),
    )

    # G-060: Custom roles
    op.create_table(
        "custom_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("role_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("permissions", sa.Text, nullable=False, server_default="[]"),
        sa.Column("base_template", sa.String(50), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("organization_id", "role_name", name="uq_org_role_name"),
    )
    op.create_index("ix_custom_roles_org", "custom_roles", ["organization_id"])

    # G-034: Board portal access tokens
    op.create_table(
        "board_access_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("allowed_sections", sa.Text, nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("shared_with_email", sa.String(254), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_bat_org", "board_access_tokens", ["organization_id"])
    op.create_index("ix_bat_report", "board_access_tokens", ["report_id"])
    op.create_unique_constraint("uq_bat_token_hash", "board_access_tokens", ["token_hash"])
    op.create_index("ix_bat_token_hash", "board_access_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("board_access_tokens")
    op.drop_table("custom_roles")
    op.drop_table("organization_settings")
