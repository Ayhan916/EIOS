"""M48.2 G-060 — Custom Role Builder."""

from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CustomRoleModel(Base):
    """A custom RBAC role defined by an admin within an organization.

    Permissions are stored as a JSON array of {resource, actions[]} objects.
    Example:
      [{"resource": "finding", "actions": ["read", "update"]},
       {"resource": "risk",    "actions": ["read"]}]
    """

    __tablename__ = "custom_roles"
    __table_args__ = (UniqueConstraint("organization_id", "role_name", name="uq_org_role_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # JSON: list of {resource: str, actions: list[str]}
    permissions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # Template this role was derived from (e.g. "viewer", "analyst", "auditor")
    base_template: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


# Built-in template definitions (used for seeding / UI presets)
ROLE_TEMPLATES = {
    "viewer": {
        "description": "Read-only access to all modules",
        "permissions": [
            {"resource": "*", "actions": ["read"]},
        ],
    },
    "analyst": {
        "description": "Read + update on assessments, findings, risks, and evidence",
        "permissions": [
            {"resource": "assessment", "actions": ["read", "update"]},
            {"resource": "finding", "actions": ["read", "update", "create"]},
            {"resource": "risk", "actions": ["read", "update", "create"]},
            {"resource": "evidence", "actions": ["read", "create"]},
        ],
    },
    "auditor": {
        "description": "Read-only with audit trail access",
        "permissions": [
            {"resource": "*", "actions": ["read"]},
            {"resource": "audit_log", "actions": ["read", "export"]},
        ],
    },
    "supplier_manager": {
        "description": "Manage suppliers and due diligence",
        "permissions": [
            {"resource": "supplier", "actions": ["read", "create", "update"]},
            {"resource": "due_diligence", "actions": ["read", "create", "update"]},
            {"resource": "finding", "actions": ["read"]},
        ],
    },
}
