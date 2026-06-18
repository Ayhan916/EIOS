import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status

import application.audit as audit_factory
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.repositories import SQLAuditEventRepository, SQLUserRepository
from interfaces.api.deps import (
    get_audit_event_repo,
    get_current_user,
    get_user_repo,
    require_admin,
)
from interfaces.api.schemas.user import (
    UserInviteRequest,
    UserInviteResponse,
    UserResponse,
    UserUpdate,
)
from shared.email import send_email
from shared.security import hash_password

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)

_TEMP_PW_CHARS = string.ascii_letters + string.digits + "!@#$"
_TEMP_PW_LEN = 12


def _generate_temp_password() -> str:
    return "".join(secrets.choice(_TEMP_PW_CHARS) for _ in range(_TEMP_PW_LEN))


@router.get("/", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
async def list_org_users(
    current_user: User = Depends(get_current_user),
    repo: SQLUserRepository = Depends(get_user_repo),
) -> list[UserResponse]:
    if not current_user.organization_id:
        return []
    users = await repo.list_by_organization(current_user.organization_id)
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
)
async def update_user(
    user_id: str,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    repo: SQLUserRepository = Depends(get_user_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> UserResponse:
    target = await repo.get_by_id(user_id)
    if target is None or target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own account via this endpoint",
        )

    changed = body.model_fields_set

    # Guard: prevent an operation that would leave no active admin besides the actor.
    # We exclude both the target and the actor from the count: if the result is 0, the
    # operation would reduce the org to a single active admin (the actor) with no one else
    # able to manage the org if the actor leaves.
    will_lose_admin = (
        target.role == "admin"
        and target.is_active
        and (
            ("role" in changed and body.role is not None and body.role.value != "admin")
            or ("is_active" in changed and body.is_active is False)
        )
    )
    if will_lose_admin:
        org_users = await repo.list_by_organization(current_user.organization_id)
        other_active_admins = sum(
            1
            for u in org_users
            if u.role == "admin"
            and u.is_active
            and u.id != target.id
            and u.id != current_user.id
        )
        if other_active_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote or deactivate the last active admin of the organization",
            )

    if "role" in changed and body.role is not None:
        target.role = body.role.value
    if "is_active" in changed and body.is_active is not None:
        target.is_active = body.is_active
    if "display_name" in changed and body.display_name is not None:
        target.display_name = body.display_name
    target.updated_by = current_user.id

    saved = await repo.save(target)

    await audit_repo.save(
        audit_factory.user_updated(
            target_user_id=user_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
            changes={k: str(getattr(body, k)) for k in changed},
        )
    )

    return UserResponse.model_validate(saved)


@router.post(
    "/invite",
    response_model=UserInviteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def invite_user(
    body: UserInviteRequest,
    current_user: User = Depends(get_current_user),
    repo: SQLUserRepository = Depends(get_user_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
) -> UserInviteResponse:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin has no organization",
        )

    existing = await repo.get_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    temp_password = _generate_temp_password()
    new_user = User(
        email=body.email,
        display_name=body.display_name,
        role=body.role.value,
        organization_id=current_user.organization_id,
        is_active=True,
        status=EntityStatus.ACTIVE,
        password_hash=hash_password(temp_password),
        created_by=current_user.id,
    )
    saved = await repo.save(new_user)

    await audit_repo.save(
        audit_factory.user_invited(
            new_user_id=saved.id,
            new_user_email=saved.email,
            actor_id=current_user.id,
            actor_email=current_user.email,
            organization_id=current_user.organization_id,
        )
    )

    # Send invite email when SMTP is configured.
    # The temp password is never stored in logs — only hashed in DB and returned here once.
    await send_email(
        to=saved.email,
        subject=f"You have been invited to EIOS by {current_user.display_name}",
        body_html=(
            f"<p>Hello {saved.display_name},</p>"
            f"<p>Your temporary password is: <strong>{temp_password}</strong></p>"
            f"<p>Please sign in and change it immediately.</p>"
        ),
        body_text=(
            f"Hello {saved.display_name},\n\n"
            f"Your temporary password is: {temp_password}\n\n"
            f"Please sign in and change it immediately."
        ),
    )

    return UserInviteResponse(
        user=UserResponse.model_validate(saved),
        temp_password=temp_password,
    )
