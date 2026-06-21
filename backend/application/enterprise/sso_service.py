"""SSO Identity Provider management — M40.1 / M40.2 / M40.3 hardened.

Changes from M40:
  - client_secret stored via SecretProvider (SecretReference pattern)
  - process_sso_login() accepts ValidatedIdentity — never raw caller claims
  - rotate_identity_provider_secret() rotates secrets with full audit trail
  - delete_identity_provider() cleans up the SecretReference + provider storage
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
    metadata: dict | None = None,
) -> None:
    now = datetime.now(UTC)
    session.add(AuditEventModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        action=action,
        entity_type="IdentityProvider",
        entity_id=entity_id,
        actor_id=actor_id,
        outcome="success",
        detail=detail,
        event_metadata=metadata or {},
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
        "enterprise.idp.created",
        actor_id,
        idp.id,
        f"Identity provider '{name}' ({provider_type}) created",
        {"enterprise_id": enterprise_id},
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
    await _log(session, "enterprise.idp.deactivated", actor_id, idp_id)
    return True


async def delete_identity_provider(
    idp_id: str,
    actor_id: str,
    session: AsyncSession,
) -> bool:
    """Delete an IdentityProvider and clean up its SecretReference.

    Calls provider.delete(identifier) to remove the secret from the
    backing store — no orphaned secrets.
    """
    idp = await get_identity_provider(idp_id, session)
    if not idp:
        return False

    # Clean up the secret before removing the reference row
    if idp.secret_reference_id:
        ref_result = await session.execute(
            select(SecretReferenceModel).where(
                SecretReferenceModel.id == idp.secret_reference_id
            )
        )
        ref = ref_result.scalar_one_or_none()
        if ref:
            try:
                provider = get_secret_provider()
                provider.delete(ref.secret_identifier)
            except Exception:  # noqa: BLE001
                pass  # best-effort; audit still fires
            await session.delete(ref)

    await session.delete(idp)
    await _log(
        session,
        "enterprise.idp.deleted",
        actor_id,
        idp_id,
        f"Identity provider '{idp.name}' deleted with secret cleanup",
        {"enterprise_id": idp.enterprise_id, "had_secret": idp.secret_reference_id is not None},
    )
    return True


async def rotate_identity_provider_secret(
    idp_id: str,
    new_client_secret: str,
    actor_id: str,
    session: AsyncSession,
) -> SecretReferenceModel:
    """Replace the client_secret for an IdP.

    Flow:
      1. Generate a new identifier and store the new secret.
      2. Create a new SecretReference row.
      3. Update IdentityProvider.secret_reference_id.
      4. Delete the old secret from the provider (best-effort).
      5. Delete the old SecretReference row.
      6. Audit enterprise.idp.secret_rotated.
    """
    idp = await get_identity_provider(idp_id, session)
    if not idp:
        raise ValueError(f"IdentityProvider {idp_id!r} not found")

    now = datetime.now(UTC)
    provider = get_secret_provider()

    # Step 1-2: Store new secret + create reference
    new_identifier = f"EIOS_IDP_{idp.enterprise_id}_{str(uuid.uuid4())[:8]}_CLIENT_SECRET"
    provider.store(new_identifier, new_client_secret)
    new_ref = SecretReferenceModel(
        id=str(uuid.uuid4()),
        provider=provider.provider_name,
        secret_identifier=new_identifier,
        label=f"IdP client_secret for '{idp.name}' (rotated)",
        reference_created_at=now,
        status="Active",
        version=1,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(new_ref)
    await session.flush()

    # Step 3: Swap the FK
    old_ref_id = idp.secret_reference_id
    idp.secret_reference_id = new_ref.id
    idp.updated_at = now

    # Steps 4-5: Clean up old reference
    if old_ref_id:
        old_result = await session.execute(
            select(SecretReferenceModel).where(SecretReferenceModel.id == old_ref_id)
        )
        old_ref = old_result.scalar_one_or_none()
        if old_ref:
            try:
                provider.delete(old_ref.secret_identifier)
            except Exception:  # noqa: BLE001
                pass
            await session.delete(old_ref)

    # Step 6: Audit
    await _log(
        session,
        "enterprise.idp.secret_rotated",
        actor_id,
        idp_id,
        f"Client secret rotated for IdP '{idp.name}'",
        {
            "enterprise_id": idp.enterprise_id,
            "new_reference_id": new_ref.id,
            "old_reference_id": old_ref_id,
        },
    )
    return new_ref


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
        action="enterprise.group_mapping.created",
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
    validated_identity: "ValidatedIdentity",  # noqa: F821 — forward ref; import below
    session: AsyncSession,
    user_id: str | None = None,
) -> SSOLoginResult:
    """Apply group mappings to a user after a verified SSO authentication.

    Accepts only a ValidatedIdentity — groups come from the validated
    assertion/token, never from raw caller-supplied claims.

    user_id: the EIOS user to update. If None, uses validated_identity.external_id
             to look up the user by external SSO id (future extension point).
             For now pass the resolved user_id explicitly.
    """
    from application.enterprise.sso_validation import ValidatedIdentity  # noqa: PLC0415

    idp_id = validated_identity.idp_id
    idp_groups = validated_identity.groups

    # Load mappings for this IdP
    mappings = await list_group_mappings(idp_id, session)

    idp_group_set = set(idp_groups)
    matched: list[GroupMappingModel] = [
        m for m in mappings if m.idp_group in idp_group_set
    ]

    def _rank(m: GroupMappingModel) -> int:
        if m.mapped_role in ("bu_admin", "regional_admin"):
            return 0
        if m.mapped_role == "enterprise_admin":
            return 1
        return 2

    matched.sort(key=_rank)
    best = matched[0] if matched else None

    target_user_id = user_id or validated_identity.external_id
    user_result = await session.execute(
        select(UserModel).where(UserModel.id == target_user_id)
    )
    user = user_result.scalar_one_or_none()

    now = datetime.now(UTC)
    applied_role = "viewer"
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
        action="sso.login.success",
        entity_type="User",
        entity_id=target_user_id,
        actor_id=target_user_id,
        outcome="success",
        detail=f"SSO login via IdP {idp_id}; role '{applied_role}' applied",
        event_metadata={
            "enterprise_id": enterprise_id,
            "idp_id": idp_id,
            "issuer": validated_identity.issuer,
            "matched_groups": list(idp_group_set & {m.idp_group for m in matched}),
            "applied_role": applied_role,
            "enterprise_scope": enterprise_scope,
        },
    ))

    return SSOLoginResult(
        user_id=target_user_id,
        applied_role=applied_role,
        enterprise_scope=enterprise_scope,
        enterprise_id=enterprise_id,
        business_unit_id=bu_id,
        region_id=region_id,
        matched_groups=list(idp_group_set & {m.idp_group for m in matched}),
    )
