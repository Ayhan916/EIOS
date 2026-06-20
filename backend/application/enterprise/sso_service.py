"""SSO Identity Provider configuration management — M40.1 hardened.

Changes from M40:
  - client_secret is stored via SecretProvider (never in the DB column directly)
  - IdentityProvider.secret_reference_id points to a SecretReferenceModel row
  - process_sso_login() enforces group mappings at login time
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_event import AuditEventModel
from infrastructure.persistence.models.enterprise import (
    GroupMappingModel,
    IdentityProviderModel,
    SecretReferenceModel,
)
from infrastructure.persistence.models.user import UserModel
from infrastructure.secrets.provider import get_secret_provider


async def _log(
    session: AsyncSession,
    action: str,
    actor_id: str | None,
    entity_id: str,
    detail: str = "",
) -> None:
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        action=action,
        entity_type="IdentityProvider",
        entity_id=entity_id,
        actor_id=actor_id,
        outcome="success",
        detail=detail,
        event_metadata={},
    ))


async def create_identity_provider(
    enterprise_id: str,
    name: str,
    provider_type: str,
    issuer: str | None,
    metadata_url: str | None,
    client_id: str | None,
    client_secret: str | None,
    certificates: list[str],
    config: dict,
    actor_id: str,
    session: AsyncSession,
) -> IdentityProviderModel:
    now = datetime.now(UTC)

    secret_ref_id: str | None = None
    if client_secret:
        provider = get_secret_provider()
        # identifier: enterprise-scoped so secrets don't collide across enterprises
        identifier = f"EIOS_IDP_{enterprise_id}_{str(uuid.uuid4())[:8]}_CLIENT_SECRET"
        provider.store(identifier, client_secret)

        ref = SecretReferenceModel(
            id=str(uuid.uuid4()),
            provider=provider.provider_name,
            secret_identifier=identifier,
            label=f"IdP client_secret for '{name}'",
            reference_created_at=now,
            status="Active",
            version=1,
            created_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        session.add(ref)
        await session.flush()
        secret_ref_id = ref.id

    idp = IdentityProviderModel(
        id=str(uuid.uuid4()),
        enterprise_id=enterprise_id,
        name=name,
        provider_type=provider_type,
        issuer=issuer,
        metadata_url=metadata_url,
        client_id=client_id,
        secret_reference_id=secret_ref_id,
        certificates=certificates,
        config=config,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(idp)
    await session.flush()
    await _log(
        session,
        "idp.created",
        actor_id,
        idp.id,
        f"Identity provider '{name}' ({provider_type}) created",
    )
    return idp


async def get_identity_provider(
    idp_id: str, session: AsyncSession
) -> IdentityProviderModel | None:
    result = await session.execute(
        select(IdentityProviderModel).where(IdentityProviderModel.id == idp_id)
    )
    return result.scalar_one_or_none()


async def list_identity_providers(
    enterprise_id: str, session: AsyncSession
) -> list[IdentityProviderModel]:
    result = await session.execute(
        select(IdentityProviderModel).where(
            IdentityProviderModel.enterprise_id == enterprise_id,
            IdentityProviderModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def deactivate_identity_provider(
    idp_id: str, actor_id: str, session: AsyncSession
) -> bool:
    idp = await get_identity_provider(idp_id, session)
    if not idp:
        return False
    idp.is_active = False
    idp.updated_at = datetime.now(UTC)
    await _log(session, "idp.deactivated", actor_id, idp_id)
    return True


async def create_group_mapping(
    idp_id: str,
    enterprise_id: str,
    idp_group: str,
    mapped_role: str,
    scope: str | None,
    business_unit_id: str | None,
    region_id: str | None,
    actor_id: str,
    session: AsyncSession,
) -> GroupMappingModel:
    now = datetime.now(UTC)
    mapping = GroupMappingModel(
        id=str(uuid.uuid4()),
        idp_id=idp_id,
        enterprise_id=enterprise_id,
        idp_group=idp_group,
        mapped_role=mapped_role,
        scope=scope,
        business_unit_id=business_unit_id,
        region_id=region_id,
        is_active=True,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(mapping)
    await session.flush()
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        action="idp.group_mapping_created",
        entity_type="GroupMapping",
        entity_id=mapping.id,
        actor_id=actor_id,
        outcome="success",
        detail=f"Group '{idp_group}' → role '{mapped_role}'",
        event_metadata={"idp_id": idp_id},
    ))
    return mapping


async def list_group_mappings(
    idp_id: str, session: AsyncSession
) -> list[GroupMappingModel]:
    result = await session.execute(
        select(GroupMappingModel).where(
            GroupMappingModel.idp_id == idp_id,
            GroupMappingModel.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


# ── SSO Login Enforcement ─────────────────────────────────────────────────────


class SSOLoginResult:
    """Result of processing an SSO login callback."""

    def __init__(
        self,
        user_id: str,
        applied_role: str,
        enterprise_scope: str | None,
        enterprise_id: str | None,
        business_unit_id: str | None,
        region_id: str | None,
        matched_groups: list[str],
    ) -> None:
        self.user_id = user_id
        self.applied_role = applied_role
        self.enterprise_scope = enterprise_scope
        self.enterprise_id = enterprise_id
        self.business_unit_id = business_unit_id
        self.region_id = region_id
        self.matched_groups = matched_groups

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "applied_role": self.applied_role,
            "enterprise_scope": self.enterprise_scope,
            "enterprise_id": self.enterprise_id,
            "business_unit_id": self.business_unit_id,
            "region_id": self.region_id,
            "matched_groups": self.matched_groups,
        }


async def process_sso_login(
    enterprise_id: str,
    idp_id: str,
    user_id: str,
    idp_groups: list[str],
    session: AsyncSession,
) -> SSOLoginResult:
    """Apply group mappings and update user scopes after a successful SSO authentication.

    Flow:
      1. Load all active group mappings for the IdP.
      2. Match the user's IdP group claims against the mapping table.
         - Specificity order: bu_admin / regional_admin > enterprise_admin > bare role.
         - First match in declared order wins if no scoped match exists.
      3. Apply the matched role + enterprise scope to the user record.
      4. Write an audit event.

    This function is called by the SSO callback handler (OIDC redirect / SAML ACS)
    after the identity has been verified — it must NOT perform identity verification.
    """
    # Load mappings for this IdP
    mappings = await list_group_mappings(idp_id, session)

    # Build a lookup: idp_group → mapping (keep only active, matching groups)
    idp_group_set = set(idp_groups)
    matched: list[GroupMappingModel] = [
        m for m in mappings if m.idp_group in idp_group_set
    ]

    # Rank matches: scoped roles (bu_admin, regional_admin) > enterprise_admin > others
    def _rank(m: GroupMappingModel) -> int:
        if m.mapped_role in ("bu_admin", "regional_admin"):
            return 0
        if m.mapped_role == "enterprise_admin":
            return 1
        return 2

    matched.sort(key=_rank)

    best = matched[0] if matched else None

    # Resolve the user from the DB
    user_result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    now = datetime.now(UTC)
    applied_role = "viewer"  # fallback
    enterprise_scope: str | None = None
    bu_id: str | None = None
    region_id: str | None = None

    if best is not None:
        applied_role = best.mapped_role
        enterprise_scope = best.scope
        bu_id = best.business_unit_id
        region_id = best.region_id

    if user is not None:
        user.role = applied_role
        user.enterprise_id = enterprise_id
        user.enterprise_scope = enterprise_scope
        user.business_unit_id = bu_id
        user.region_id = region_id
        user.updated_at = now

    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        action="sso.login",
        entity_type="User",
        entity_id=user_id,
        actor_id=user_id,
        outcome="success",
        detail=f"SSO login via IdP {idp_id}; role '{applied_role}' applied",
        event_metadata={
            "enterprise_id": enterprise_id,
            "idp_id": idp_id,
            "matched_groups": list(idp_group_set & {m.idp_group for m in matched}),
            "applied_role": applied_role,
            "enterprise_scope": enterprise_scope,
        },
    ))

    return SSOLoginResult(
        user_id=user_id,
        applied_role=applied_role,
        enterprise_scope=enterprise_scope,
        enterprise_id=enterprise_id,
        business_unit_id=bu_id,
        region_id=region_id,
        matched_groups=list(idp_group_set & {m.idp_group for m in matched}),
    )
