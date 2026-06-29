"""Unit tests for the UserRole enum and RBAC helper (M13)."""

from __future__ import annotations

import pytest

from domain.enums import UserRole, has_min_role


class TestUserRoleEnum:
    def test_role_values(self) -> None:
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.REVIEWER.value == "reviewer"
        assert UserRole.ADMIN.value == "admin"

    def test_role_is_str(self) -> None:
        assert isinstance(UserRole.ADMIN, str)
        assert UserRole.ADMIN == "admin"

    def test_role_from_string(self) -> None:
        assert UserRole("viewer") == UserRole.VIEWER
        assert UserRole("admin") == UserRole.ADMIN

    def test_invalid_role_raises(self) -> None:
        with pytest.raises(ValueError):
            UserRole("superuser")


class TestHasMinRole:
    def test_admin_meets_all_roles(self) -> None:
        for min_role in UserRole:
            assert has_min_role("admin", min_role)

    def test_viewer_meets_only_viewer(self) -> None:
        assert has_min_role("viewer", UserRole.VIEWER)
        assert not has_min_role("viewer", UserRole.ANALYST)
        assert not has_min_role("viewer", UserRole.REVIEWER)
        assert not has_min_role("viewer", UserRole.ADMIN)

    def test_analyst_meets_viewer_and_analyst(self) -> None:
        assert has_min_role("analyst", UserRole.VIEWER)
        assert has_min_role("analyst", UserRole.ANALYST)
        assert not has_min_role("analyst", UserRole.REVIEWER)
        assert not has_min_role("analyst", UserRole.ADMIN)

    def test_reviewer_meets_viewer_analyst_reviewer(self) -> None:
        assert has_min_role("reviewer", UserRole.VIEWER)
        assert has_min_role("reviewer", UserRole.ANALYST)
        assert has_min_role("reviewer", UserRole.REVIEWER)
        assert not has_min_role("reviewer", UserRole.ADMIN)

    def test_empty_string_fails_all(self) -> None:
        for min_role in UserRole:
            assert not has_min_role("", min_role)

    def test_unknown_role_fails_all(self) -> None:
        for min_role in UserRole:
            assert not has_min_role("superuser", min_role)

    def test_case_sensitive(self) -> None:
        assert not has_min_role("Admin", UserRole.VIEWER)
        assert not has_min_role("ADMIN", UserRole.VIEWER)

    def test_ordering_is_strict(self) -> None:
        # reviewer does NOT meet admin
        assert not has_min_role("reviewer", UserRole.ADMIN)
        # analyst does NOT meet reviewer
        assert not has_min_role("analyst", UserRole.REVIEWER)

    def test_exact_match_satisfies(self) -> None:
        assert has_min_role("reviewer", UserRole.REVIEWER)
        assert has_min_role("analyst", UserRole.ANALYST)

    def test_accepts_userrole_string_value(self) -> None:
        # UserRole values are strings; confirm they work directly
        assert has_min_role(UserRole.ADMIN.value, UserRole.VIEWER)
        assert has_min_role(UserRole.ANALYST.value, UserRole.ANALYST)


class TestRoleOrdering:
    def test_viewer_is_lowest(self) -> None:
        # viewer cannot satisfy analyst minimum
        assert not has_min_role("viewer", UserRole.ANALYST)

    def test_admin_is_highest(self) -> None:
        # admin satisfies all
        for min_role in [UserRole.VIEWER, UserRole.ANALYST, UserRole.REVIEWER, UserRole.ADMIN]:
            assert has_min_role("admin", min_role)

    def test_role_chain(self) -> None:
        # analyst >= viewer (True), reviewer >= analyst (True), admin >= reviewer (True)
        assert has_min_role("analyst", UserRole.VIEWER)
        assert has_min_role("reviewer", UserRole.ANALYST)
        assert has_min_role("admin", UserRole.REVIEWER)
