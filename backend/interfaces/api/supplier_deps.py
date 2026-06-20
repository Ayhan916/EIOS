"""M35 Supplier Portal — FastAPI dependency injection.

Completely separate authentication boundary from internal users.

Key dependencies:
  get_current_supplier_user()  — validates aud=eios-supplier JWT
  require_supplier_manager()   — enforces SUPPLIER_MANAGER role
  require_same_supplier()      — guards any resource with a supplier_id param

Design principles:
  - Supplier tokens are REJECTED by get_current_user() in deps.py
  - Internal tokens are REJECTED by get_current_supplier_user() here
  - supplier_id is always validated against the authenticated user's supplier_id
"""

from __future__ import annotations

from collections.abc import Callable

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import SupplierUserRole
from domain.supplier_portal import SupplierUser
from interfaces.api.deps import get_db
from shared.security import decode_supplier_token

_bearer = HTTPBearer(auto_error=False)
_bearer_required = HTTPBearer(auto_error=True)


async def get_current_supplier_user(
    request: Request,
    credentials=Depends(_bearer_required),
    session: AsyncSession = Depends(get_db),
) -> SupplierUser:
    """Validate a supplier JWT and load the SupplierUser.

    Rejects tokens without aud=eios-supplier.
    Rejects inactive supplier users.
    """
    from infrastructure.persistence.models.supplier_portal import SupplierUserModel
    from sqlalchemy import select
    from datetime import UTC, datetime

    token = credentials.credentials
    try:
        payload = decode_supplier_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supplier session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience — use supplier credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid supplier token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplier_user_id = payload.get("sub")
    if not supplier_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supplier token missing subject",
        )

    stmt = (
        select(SupplierUserModel)
        .where(SupplierUserModel.id == supplier_user_id)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None or not row.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supplier user not found or inactive",
        )

    return SupplierUser(
        id=row.id,
        supplier_id=row.supplier_id,
        email=row.email,
        display_name=row.display_name,
        role=row.role,
        is_active=row.is_active,
        last_login_at=row.last_login_at,
        invited_at=row.invited_at,
        accepted_at=row.accepted_at,
        notification_preferences=row.notification_preferences or {},
    )


def require_supplier_manager() -> Callable:
    """Enforce SUPPLIER_MANAGER role for supplier users."""

    async def _check(
        supplier_user: SupplierUser = Depends(get_current_supplier_user),
    ) -> SupplierUser:
        if supplier_user.role != SupplierUserRole.SUPPLIER_MANAGER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supplier Manager role required",
            )
        return supplier_user

    return _check


def guard_supplier_resource(supplier_id: str, supplier_user: SupplierUser) -> None:
    """Raise 403 if supplier_user.supplier_id != supplier_id.

    Call this at the start of any endpoint that exposes a supplier-scoped
    resource to ensure strict isolation (no cross-supplier access).
    """
    if supplier_user.supplier_id != supplier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this supplier's data is not permitted",
        )
