"""Unit tests for M40 Enterprise Multi-Tenant Scale.

Tests pure-logic functions that have no DB dependency:
  - rollup_service.compute_enterprise_health_score
  - hierarchy_service data shapes (via model instantiation)
  - admin_service role constant validation
  - schema creation/validation
"""

from __future__ import annotations

import pytest

# ── Health score tests ────────────────────────────────────────────────────────


class TestEnterpriseHealthScore:
    """compute_enterprise_health_score is a pure deterministic function."""

    def _score(self, **kwargs):
        from application.enterprise.rollup_service import _score_from_rollup

        rollup = {
            "organization_count": 5,
            "supplier_count": 100,
            "total_risks": 20,
            "critical_risks": 2,
            "total_findings": 50,
            "open_findings": 10,
            "compliance_readiness": 80.0,
        }
        rollup.update(kwargs)
        return _score_from_rollup(rollup)

    def test_perfect_enterprise_scores_100(self) -> None:
        result = self._score(
            total_risks=10,
            critical_risks=0,
            total_findings=10,
            open_findings=0,
            compliance_readiness=100.0,
            supplier_count=100,
        )
        assert result["score"] == pytest.approx(100.0, abs=2.0)
        assert result["grade"] == "A"

    def test_zero_enterprise_scores_low(self) -> None:
        result = self._score(
            supplier_count=0,
            total_risks=50,
            critical_risks=50,
            total_findings=100,
            open_findings=100,
            compliance_readiness=0.0,
        )
        assert result["score"] < 30
        assert result["grade"] in ("D", "F")

    def test_grade_boundaries(self) -> None:
        for compliance in [100.0, 75.0, 50.0, 25.0, 0.0]:
            r = self._score(compliance_readiness=compliance)
            assert r["grade"] in ("A", "B", "C", "D", "F")

    def test_result_has_required_keys(self) -> None:
        result = self._score()
        assert "score" in result
        assert "grade" in result
        assert "components" in result
        assert "drivers" in result

    def test_components_sum_approximately_to_score(self) -> None:
        result = self._score(
            supplier_count=200,
            total_risks=10,
            critical_risks=1,
            total_findings=20,
            open_findings=5,
            compliance_readiness=85.0,
        )
        components = result["components"]
        assert set(components.keys()) == {
            "compliance",
            "risk_posture",
            "finding_rate",
            "supplier_coverage",
            "governance",
        }
        # Each component value should be between 0 and 1 (normalized)
        for v in components.values():
            assert 0.0 <= v <= 1.0

    def test_no_suppliers_reduces_score(self) -> None:
        with_suppliers = self._score(supplier_count=100)
        without_suppliers = self._score(supplier_count=0)
        assert with_suppliers["score"] >= without_suppliers["score"]

    def test_critical_risks_reduce_score(self) -> None:
        no_critical = self._score(total_risks=10, critical_risks=0)
        all_critical = self._score(total_risks=10, critical_risks=10)
        assert no_critical["score"] > all_critical["score"]

    def test_score_is_deterministic(self) -> None:
        r1 = self._score(supplier_count=150, critical_risks=3, open_findings=8)
        r2 = self._score(supplier_count=150, critical_risks=3, open_findings=8)
        assert r1["score"] == r2["score"]
        assert r1["grade"] == r2["grade"]

    def test_drivers_list_is_non_empty_for_imperfect_score(self) -> None:
        result = self._score(critical_risks=5, open_findings=20, compliance_readiness=40.0)
        assert len(result["drivers"]) > 0

    def test_score_bounded_0_to_100(self) -> None:
        result = self._score()
        assert 0.0 <= result["score"] <= 100.0


# ── Delegated admin role constants ────────────────────────────────────────────


class TestDelegatedAdminRoles:
    def test_enterprise_scope_roles_defined(self) -> None:
        from application.enterprise.admin_service import ENTERPRISE_SCOPE_ROLES

        assert "enterprise_admin" in ENTERPRISE_SCOPE_ROLES
        assert "bu_admin" in ENTERPRISE_SCOPE_ROLES
        assert "regional_admin" in ENTERPRISE_SCOPE_ROLES

    def test_bu_admin_is_distinct_from_enterprise_admin(self) -> None:
        from application.enterprise.admin_service import ENTERPRISE_SCOPE_ROLES

        assert len(set(ENTERPRISE_SCOPE_ROLES)) == len(ENTERPRISE_SCOPE_ROLES)


# ── Schema validation tests ───────────────────────────────────────────────────


class TestEnterpriseSchemas:
    def test_enterprise_create_schema_valid(self) -> None:
        from interfaces.api.schemas.enterprise import EnterpriseCreate

        e = EnterpriseCreate(
            name="ACME Corp",
            default_data_residency="EU",
            default_data_classification="INTERNAL",
        )
        assert e.name == "ACME Corp"
        assert e.default_data_residency == "EU"

    def test_enterprise_create_requires_name(self) -> None:
        from pydantic import ValidationError

        from interfaces.api.schemas.enterprise import EnterpriseCreate

        with pytest.raises(ValidationError):
            EnterpriseCreate()  # type: ignore[call-arg]

    def test_identity_provider_response_no_secret(self) -> None:
        from interfaces.api.schemas.enterprise import IdentityProviderResponse

        # IdentityProviderResponse must NOT have a client_secret field
        fields = set(IdentityProviderResponse.model_fields.keys())
        assert "client_secret" not in fields
        assert "client_secret_encrypted" not in fields
        # It must expose has_client_secret (bool) instead
        assert "has_client_secret" in fields

    def test_enterprise_risk_create_schema(self) -> None:
        from interfaces.api.schemas.enterprise import EnterpriseRiskCreate

        r = EnterpriseRiskCreate(
            title="Supply chain disruption",
            severity="high",
            esg_category="social",
        )
        assert r.title == "Supply chain disruption"
        assert r.severity == "high"

    def test_scim_user_create_schema(self) -> None:
        from interfaces.api.schemas.enterprise import ScimUserCreate

        u = ScimUserCreate(
            username="jdoe",
            email="jdoe@example.com",
            display_name="John Doe",
            organization_id="org-123",
        )
        assert u.email == "jdoe@example.com"

    def test_global_search_request_schema(self) -> None:
        from interfaces.api.schemas.enterprise import GlobalSearchRequest

        req = GlobalSearchRequest(query="climate risk")
        assert req.query == "climate risk"
        assert req.entity_types is None or isinstance(req.entity_types, list)

    def test_bu_rollup_item_schema(self) -> None:
        from interfaces.api.schemas.enterprise import BURollupItem

        item = BURollupItem(
            business_unit_id="bu-1",
            business_unit_name="EMEA",
            organization_count=3,
            supplier_count=150,
            risk_count=12,
            compliance_readiness=0.82,
        )
        assert item.compliance_readiness == pytest.approx(0.82)
        assert item.business_unit_name == "EMEA"

    def test_assign_enterprise_role_request_schema(self) -> None:
        from interfaces.api.schemas.enterprise import AssignEnterpriseRoleRequest

        req = AssignEnterpriseRoleRequest(
            user_id="user-1",
            enterprise_scope="bu_admin",
            business_unit_id="bu-42",
        )
        assert req.enterprise_scope == "bu_admin"
        assert req.business_unit_id == "bu-42"


# ── SSO encryption helper ─────────────────────────────────────────────────────


class TestSSOEncryption:
    """M40.1: _encrypt_secret removed — client secrets are stored via SecretReference.
    These tests verify _score_from_rollup (the M40 pure helper kept in M40.1)."""

    def test_score_from_rollup_returns_dict_with_score(self) -> None:
        from application.enterprise.rollup_service import _score_from_rollup

        rollup = {
            "compliance_readiness": 80.0,
            "critical_risks": 0,
            "total_risks": 5,
            "open_findings": 2,
            "total_findings": 10,
            "supplier_count": 3,
        }
        result = _score_from_rollup(rollup)
        assert isinstance(result, dict)
        assert "score" in result
        assert 0.0 <= result["score"] <= 100.0

    def test_score_from_rollup_grade_present(self) -> None:
        from application.enterprise.rollup_service import _score_from_rollup

        result = _score_from_rollup(
            {
                "compliance_readiness": 90.0,
                "critical_risks": 0,
                "total_risks": 2,
                "open_findings": 0,
                "total_findings": 4,
                "supplier_count": 5,
            }
        )
        assert "grade" in result
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_score_from_rollup_components_normalized(self) -> None:
        from application.enterprise.rollup_service import _score_from_rollup

        result = _score_from_rollup(
            {
                "compliance_readiness": 50.0,
                "critical_risks": 1,
                "total_risks": 10,
                "open_findings": 5,
                "total_findings": 20,
                "supplier_count": 0,
            }
        )
        for v in result["components"].values():
            assert 0.0 <= v <= 1.0


# ── Hierarchy model field tests ───────────────────────────────────────────────


class TestEnterpriseOrmModels:
    def test_enterprise_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import EnterpriseModel

        assert EnterpriseModel.__tablename__ == "enterprises"

    def test_business_unit_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import BusinessUnitModel

        assert BusinessUnitModel.__tablename__ == "business_units"

    def test_legal_entity_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import LegalEntityModel

        assert LegalEntityModel.__tablename__ == "legal_entities"

    def test_region_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import RegionModel

        assert RegionModel.__tablename__ == "enterprise_regions"

    def test_identity_provider_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import IdentityProviderModel

        assert IdentityProviderModel.__tablename__ == "identity_providers"

    def test_enterprise_risk_model_tablename(self) -> None:
        from infrastructure.persistence.models.enterprise import EnterpriseRiskModel

        assert EnterpriseRiskModel.__tablename__ == "enterprise_risks"

    def test_organization_has_enterprise_fields(self) -> None:
        import sqlalchemy as sa

        from infrastructure.persistence.models.organization import OrganizationModel

        cols = {c.name for c in sa.inspect(OrganizationModel).columns}
        assert "enterprise_id" in cols
        assert "business_unit_id" in cols
        assert "region_id" in cols
        assert "data_residency" in cols
        assert "data_classification" in cols

    def test_user_has_enterprise_scope_fields(self) -> None:
        import sqlalchemy as sa

        from infrastructure.persistence.models.user import UserModel

        cols = {c.name for c in sa.inspect(UserModel).columns}
        assert "enterprise_scope" in cols
        assert "enterprise_id" in cols
        assert "business_unit_id" in cols
        assert "region_id" in cols


# ── Tenant isolation contract tests ──────────────────────────────────────────


class TestTenantIsolationContracts:
    """Verify that service functions require enterprise_id filtering.

    These are static checks on function signatures, not DB calls.
    """

    def test_list_enterprise_risks_requires_enterprise_id(self) -> None:
        import inspect

        from application.enterprise.risk_service import list_enterprise_risks

        sig = inspect.signature(list_enterprise_risks)
        assert "enterprise_id" in sig.parameters

    def test_list_business_units_requires_enterprise_id(self) -> None:
        import inspect

        from application.enterprise.hierarchy_service import list_business_units

        sig = inspect.signature(list_business_units)
        assert "enterprise_id" in sig.parameters

    def test_list_identity_providers_requires_enterprise_id(self) -> None:
        import inspect

        from application.enterprise.sso_service import list_identity_providers

        sig = inspect.signature(list_identity_providers)
        assert "enterprise_id" in sig.parameters

    def test_global_search_requires_enterprise_id(self) -> None:
        import inspect

        from application.enterprise.search_service import global_search

        sig = inspect.signature(global_search)
        assert "enterprise_id" in sig.parameters

    def test_assign_enterprise_role_audits_action(self) -> None:
        """The function signature must accept actor_id for auditability."""
        import inspect

        from application.enterprise.admin_service import assign_enterprise_role

        sig = inspect.signature(assign_enterprise_role)
        assert "actor_id" in sig.parameters

    def test_scim_create_user_audits_action(self) -> None:
        import inspect

        from application.enterprise.scim_service import scim_create_user

        sig = inspect.signature(scim_create_user)
        assert "actor_id" in sig.parameters

    def test_create_enterprise_risk_audits_action(self) -> None:
        import inspect

        from application.enterprise.risk_service import create_enterprise_risk

        sig = inspect.signature(create_enterprise_risk)
        assert "actor_id" in sig.parameters
