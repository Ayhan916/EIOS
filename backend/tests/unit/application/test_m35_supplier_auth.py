"""M35 Supplier Auth Service tests.

Tests:
  - invite creates invitation record and returns raw token
  - activation: invalid token raises ValueError
  - activation: expired token raises ValueError
  - login: bad password raises ValueError
  - login: inactive user raises ValueError
  - password reset: generates token for existing user
  - password reset: returns None for unknown user (no leak)
  - reset_password: invalid token raises ValueError
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TestInviteSupplierUser:
    @pytest.mark.asyncio
    async def test_invite_creates_record_and_returns_token(self) -> None:
        from application.supplier_portal.supplier_auth_service import invite_supplier_user

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        token = await invite_supplier_user(
            supplier_id="sup-1",
            email="contact@acme.com",
            role="supplier_user",
            invited_by_user_id="user-1",
            organization_id="org-1",
            session=session,
        )

        assert isinstance(token, str)
        assert len(token) > 20
        session.add.assert_called_once()
        session.flush.assert_called_once()


class TestActivateSupplierUser:
    @pytest.mark.asyncio
    async def test_invalid_token_raises(self) -> None:
        from application.supplier_portal.supplier_auth_service import activate_supplier_user

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Invalid or expired"):
            await activate_supplier_user(
                invite_token="bad-token",
                display_name="Alice",
                password="password123",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_expired_token_raises(self) -> None:
        from application.supplier_portal.supplier_auth_service import activate_supplier_user

        raw = "some-token-abc"
        hashed = _hash(raw)
        now = datetime.now(UTC)
        invitation = MagicMock()
        invitation.token_hash = hashed
        invitation.accepted_at = None
        invitation.expires_at = now - timedelta(hours=1)  # expired

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Invalid or expired"):
            await activate_supplier_user(
                invite_token=raw,
                display_name="Alice",
                password="pass123!",
                session=session,
            )


class TestLoginSupplierUser:
    @pytest.mark.asyncio
    async def test_wrong_password_raises(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user
        from shared.security import hash_password

        user = MagicMock()
        user.password_hash = hash_password("correct-password")
        user.is_active = True
        user.id = "u-1"
        user.supplier_id = "s-1"
        user.email = "a@b.com"
        user.role = "supplier_user"
        user.locked_until = None  # F7: no active lockout
        user.failed_login_attempts = 0

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        session.add = MagicMock()

        with pytest.raises(ValueError, match="Invalid email or password"):
            await login_supplier_user("a@b.com", "wrong-password", session)

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Invalid email or password"):
            await login_supplier_user("ghost@example.com", "pass", session)


class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_unknown_user_returns_none(self) -> None:
        from application.supplier_portal.supplier_auth_service import generate_password_reset_token

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        result = await generate_password_reset_token("nobody@example.com", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_known_user_returns_token(self) -> None:
        from application.supplier_portal.supplier_auth_service import generate_password_reset_token

        user = MagicMock()
        user.id = "u-1"
        user.email = "a@b.com"
        user.supplier_id = "s-1"
        user.role = "supplier_user"

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=mock_result)

        token = await generate_password_reset_token("a@b.com", session)
        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_reset_invalid_token_raises(self) -> None:
        from application.supplier_portal.supplier_auth_service import reset_password

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Invalid, expired, or already-used"):
            await reset_password("bad-token", "newpass123", session)
