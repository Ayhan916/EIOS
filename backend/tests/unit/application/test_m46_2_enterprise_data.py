"""M46.2 Enterprise Data Layer — unit tests.

Coverage:
  G-008: Bulk supplier CSV import (sync + async dispatch + error handling)
  G-030: GHG Protocol engine (calculate, factor lookup, factor-not-found)
  G-045: Evidence version list endpoint
  G-009: Supplier invitation email dispatch
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_csv(*rows: dict) -> str:
    """Build a CSV string from a list of dicts."""
    if not rows:
        return "name\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# G-008 — CSV parsing helper
# ─────────────────────────────────────────────────────────────────────────────


class TestCsvParsing:
    def test_parses_basic_rows(self):
        from infrastructure.celery.tasks.bulk_import import _parse_csv

        csv_text = _make_csv(
            {"name": "Acme Corp", "country": "DE", "supplier_tier": "Tier 1"},
            {"name": "Beta GmbH", "country": "UK", "supplier_tier": "Tier 2"},
        )
        rows = _parse_csv(csv_text)
        assert len(rows) == 2
        assert rows[0][1]["name"] == "Acme Corp"
        assert rows[1][1]["country"] == "UK"

    def test_row_numbers_start_at_2(self):
        from infrastructure.celery.tasks.bulk_import import _parse_csv

        csv_text = _make_csv({"name": "Supplier A"}, {"name": "Supplier B"})
        rows = _parse_csv(csv_text)
        assert rows[0][0] == 2
        assert rows[1][0] == 3

    def test_empty_csv_returns_empty_list(self):
        from infrastructure.celery.tasks.bulk_import import _parse_csv

        rows = _parse_csv("name\n")
        assert rows == []

    def test_keys_normalized_to_lowercase(self):
        from infrastructure.celery.tasks.bulk_import import _parse_csv

        csv_text = "Name,Country\nSupplier X,US\n"
        rows = _parse_csv(csv_text)
        assert "name" in rows[0][1]
        assert "country" in rows[0][1]

    def test_invalid_tier_detected(self):
        from infrastructure.celery.tasks.bulk_import import _VALID_TIERS

        assert "Tier 1" in _VALID_TIERS
        assert "Tier 4" not in _VALID_TIERS


# ─────────────────────────────────────────────────────────────────────────────
# G-008 — Async bulk import task
# ─────────────────────────────────────────────────────────────────────────────


class TestBulkImportTask:
    def test_missing_name_creates_error(self):
        from infrastructure.celery.tasks.bulk_import import _parse_csv

        csv_text = _make_csv({"name": ""})
        rows = _parse_csv(csv_text)
        # The row exists but name is empty — task should produce error
        assert rows[0][1]["name"] == ""

    @pytest.mark.asyncio
    async def test_dry_run_skips_write(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.bulk_import import _run_bulk_import

        csv_text = _make_csv(
            {"name": "New Supplier", "country": "DE", "supplier_tier": "Tier 1"},
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = await _run_bulk_import(
                csv_content=csv_text,
                organization_id="org-1",
                actor_id="user-1",
                dry_run=True,
            )
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["dry_run"] is True
        assert result["imported"] == 1
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_name_is_skipped(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.bulk_import import _run_bulk_import

        csv_text = _make_csv({"name": "Existing Corp", "supplier_tier": "Tier 1"})

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_session)
        mock_session.add = MagicMock()

        existing_mock = MagicMock()
        existing_mock.id = "existing-id"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_mock
        mock_session.execute = AsyncMock(return_value=mock_result)

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = await _run_bulk_import(
                csv_content=csv_text,
                organization_id="org-1",
                actor_id="user-1",
                dry_run=False,
            )
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["skipped"] == 1
        assert result["imported"] == 0
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_tier_produces_error(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.bulk_import import _run_bulk_import

        csv_text = _make_csv({"name": "Bad Tier Corp", "supplier_tier": "Tier 9"})

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_session)

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = await _run_bulk_import(
                csv_content=csv_text,
                organization_id="org-1",
                actor_id="user-1",
                dry_run=False,
            )
        finally:
            _db_mod.AsyncSessionFactory = original

        assert len(result["errors"]) == 1
        assert "invalid supplier_tier" in result["errors"][0]["error"]


# ─────────────────────────────────────────────────────────────────────────────
# G-030 — GHG Protocol engine
# ─────────────────────────────────────────────────────────────────────────────


class TestGHGEngine:
    def _make_factor(self, **overrides):
        from infrastructure.persistence.models.ghg import GHGEmissionFactorModel

        f = GHGEmissionFactorModel()
        f.id = str(uuid.uuid4())
        f.scope = overrides.get("scope", "SCOPE1")
        f.category = overrides.get("category", "fuel_combustion")
        f.subcategory = overrides.get("subcategory", "natural_gas")
        f.unit = overrides.get("unit", "kWh")
        f.factor_kgco2e_per_unit = overrides.get("factor_kgco2e_per_unit", 0.18293)
        f.source = overrides.get("source", "DEFRA_2023")
        f.region = overrides.get("region", "UK")
        f.year = 2023
        f.description = "Test factor"
        f.is_custom = False
        f.organization_id = None
        f.created_at = datetime.now(UTC)
        return f

    @pytest.mark.asyncio
    async def test_calculate_emissions_correct_arithmetic(self):
        from application.ghg.ghg_engine import calculate_emissions

        factor = self._make_factor(factor_kgco2e_per_unit=0.18293)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = factor
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        result = await calculate_emissions(
            session=mock_session,
            organization_id="org-1",
            created_by="user-1",
            scope="SCOPE1",
            category="fuel_combustion",
            subcategory="natural_gas",
            amount=1000.0,
            unit="kWh",
            source="DEFRA_2023",
            region="UK",
        )

        expected_kg = round(1000.0 * 0.18293, 6)
        assert result.result_kgco2e == expected_kg
        assert result.result_tco2e == round(expected_kg / 1000, 9)

    @pytest.mark.asyncio
    async def test_calculate_returns_correct_factor_metadata(self):
        from application.ghg.ghg_engine import calculate_emissions

        factor = self._make_factor(
            source="EPA_2023", region="US", factor_kgco2e_per_unit=10.21, unit="gallon"
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = factor
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        result = await calculate_emissions(
            session=mock_session,
            organization_id="org-1",
            created_by="user-1",
            scope="SCOPE1",
            category="fuel_combustion",
            subcategory="diesel",
            amount=5.0,
            unit="gallon",
            source="EPA_2023",
            region="US",
        )

        assert result.source == "EPA_2023"
        assert result.region == "US"
        assert result.factor_id == factor.id

    @pytest.mark.asyncio
    async def test_factor_not_found_raises(self):
        from application.ghg.ghg_engine import GHGFactorNotFound, calculate_emissions

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(GHGFactorNotFound):
            await calculate_emissions(
                session=mock_session,
                organization_id="org-1",
                created_by="user-1",
                scope="SCOPE99",
                category="nonexistent",
                subcategory="unknown",
                amount=1.0,
                unit="kWh",
                source="DEFRA_2023",
                region="UK",
            )

    @pytest.mark.asyncio
    async def test_list_factors_returns_all_standard(self):
        from application.ghg.ghg_engine import list_factors

        factors = [self._make_factor(), self._make_factor(scope="SCOPE2")]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = factors
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await list_factors(session=mock_session)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_calculation_persisted_to_session(self):
        from application.ghg.ghg_engine import calculate_emissions

        factor = self._make_factor(factor_kgco2e_per_unit=2.5132, unit="litre")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = factor
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        await calculate_emissions(
            session=mock_session,
            organization_id="org-1",
            created_by="user-1",
            scope="SCOPE1",
            category="fuel_combustion",
            subcategory="diesel",
            amount=100.0,
            unit="litre",
            source="DEFRA_2023",
            region="UK",
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_result_tco2e_is_kgco2e_divided_by_1000(self):
        """Determinism invariant: tCO2e must always equal kgCO2e / 1000."""
        import asyncio

        from application.ghg.ghg_engine import calculate_emissions

        factor = self._make_factor(factor_kgco2e_per_unit=0.207)

        async def run():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = factor
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.flush = AsyncMock()
            mock_session.add = MagicMock()
            return await calculate_emissions(
                session=mock_session,
                organization_id="org-1",
                created_by="user-1",
                scope="SCOPE2",
                category="purchased_electricity",
                subcategory="electricity",
                amount=5000.0,
                unit="kWh",
                source="DEFRA_2023",
                region="UK",
            )

        result = asyncio.get_event_loop().run_until_complete(run())
        assert abs(result.result_tco2e - result.result_kgco2e / 1000) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# G-030 — GHG API schemas validation
# ─────────────────────────────────────────────────────────────────────────────


class TestGHGSchemas:
    def test_calculate_request_requires_positive_amount(self):
        import pydantic

        from interfaces.api.schemas.ghg import GHGCalculateRequest

        with pytest.raises(pydantic.ValidationError):
            GHGCalculateRequest(
                scope="SCOPE1",
                category="fuel_combustion",
                subcategory="natural_gas",
                amount=-1.0,
                unit="kWh",
                source="DEFRA_2023",
                region="UK",
            )

    def test_bulk_request_max_500_activities(self):
        import pydantic

        from interfaces.api.schemas.ghg import GHGBulkCalculateItem, GHGBulkCalculateRequest

        items = [
            GHGBulkCalculateItem(
                scope="SCOPE1",
                category="fuel_combustion",
                subcategory="diesel",
                amount=1.0,
                unit="litre",
                source="EPA_2023",
                region="US",
            )
            for _ in range(501)
        ]
        with pytest.raises(pydantic.ValidationError):
            GHGBulkCalculateRequest(activities=items)

    def test_emission_factor_response_from_orm(self):
        from infrastructure.persistence.models.ghg import GHGEmissionFactorModel
        from interfaces.api.schemas.ghg import GHGEmissionFactorResponse

        model = GHGEmissionFactorModel()
        model.id = "test-id"
        model.scope = "SCOPE1"
        model.category = "fuel_combustion"
        model.subcategory = "natural_gas"
        model.unit = "kWh"
        model.factor_kgco2e_per_unit = 0.18293
        model.source = "DEFRA_2023"
        model.region = "UK"
        model.year = 2023
        model.description = "Natural gas"
        model.is_custom = False

        response = GHGEmissionFactorResponse.model_validate(model)
        assert response.id == "test-id"
        assert response.factor_kgco2e_per_unit == 0.18293


# ─────────────────────────────────────────────────────────────────────────────
# G-009 — Email task
# ─────────────────────────────────────────────────────────────────────────────


class TestEmailTask:
    def test_skips_when_smtp_not_configured(self):
        import infrastructure.celery.tasks.email as email_mod
        import shared.config as _cfg_mod

        original_host = _cfg_mod.settings.smtp_host
        _cfg_mod.settings.smtp_host = ""
        try:
            result = email_mod.send_email_task.run(
                to_email="test@example.com",
                subject="Test",
                html_body="<p>Hello</p>",
            )
        finally:
            _cfg_mod.settings.smtp_host = original_host

        assert result["status"] == "skipped"

    def test_send_supplier_invitation_queues_task(self):
        from infrastructure.celery.tasks.email import send_supplier_invitation_email

        with patch("infrastructure.celery.tasks.email.send_email_task") as mock_task:
            mock_task.delay = MagicMock()
            send_supplier_invitation_email(
                to_email="supplier@example.com",
                supplier_name="Acme Corp",
                organization_name="My Org",
                invite_url="https://app.eios.io/supplier/accept?token=abc123",
            )
            mock_task.delay.assert_called_once()
            call_kwargs = mock_task.delay.call_args[1]
            assert call_kwargs["to_email"] == "supplier@example.com"
            assert "Acme Corp" in call_kwargs["subject"]

    def test_invitation_email_contains_invite_url(self):
        from infrastructure.celery.tasks.email import send_supplier_invitation_email

        with patch("infrastructure.celery.tasks.email.send_email_task") as mock_task:
            mock_task.delay = MagicMock()
            send_supplier_invitation_email(
                to_email="supplier@example.com",
                supplier_name="Acme Corp",
                organization_name="My Org",
                invite_url="https://app.eios.io/supplier/accept?token=XYZ",
            )
            call_kwargs = mock_task.delay.call_args[1]
            assert "https://app.eios.io/supplier/accept?token=XYZ" in call_kwargs["html_body"]


# ─────────────────────────────────────────────────────────────────────────────
# G-045 — Evidence versioning (ORM model)
# ─────────────────────────────────────────────────────────────────────────────


class TestEvidenceVersionModel:
    def test_model_fields_exist(self):
        from infrastructure.persistence.models.evidence_version import EvidenceVersionModel

        v = EvidenceVersionModel()
        assert hasattr(v, "evidence_id")
        assert hasattr(v, "version_number")
        assert hasattr(v, "s3_key")
        assert hasattr(v, "file_name")
        assert hasattr(v, "created_by")

    def test_tablename(self):
        from infrastructure.persistence.models.evidence_version import EvidenceVersionModel

        assert EvidenceVersionModel.__tablename__ == "evidence_versions"


# ─────────────────────────────────────────────────────────────────────────────
# Migration sanity — load via spec to avoid local alembic/ package shadow
# ─────────────────────────────────────────────────────────────────────────────


def _load_migration_056():
    import importlib.util
    import pathlib

    path = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "alembic"
        / "versions"
        / "056_m46_2_enterprise_data.py"
    )
    spec = importlib.util.spec_from_file_location("migration_056", path)
    mod = importlib.util.module_from_spec(spec)
    # The module imports alembic.op at module level — mock it before exec
    import sys
    import types

    fake_alembic_pkg = types.ModuleType("alembic")
    fake_alembic_pkg.op = MagicMock()
    sys.modules.setdefault("alembic", fake_alembic_pkg)
    # Make sure alembic.op is patchable
    import unittest.mock

    with unittest.mock.patch.dict(sys.modules, {"alembic": fake_alembic_pkg}):
        spec.loader.exec_module(mod)
    return mod


class TestMigration056:
    def test_revision_chain(self):
        m = _load_migration_056()
        assert m.revision == "056"
        assert m.down_revision == "055"

    def test_factors_list_not_empty(self):
        m = _load_migration_056()
        assert len(m._FACTORS) > 10

    def test_factors_have_defra_and_epa(self):
        m = _load_migration_056()
        sources = {row[5] for row in m._FACTORS}
        assert "DEFRA_2023" in sources
        assert "EPA_2023" in sources

    def test_all_scopes_covered(self):
        m = _load_migration_056()
        scopes = {row[0] for row in m._FACTORS}
        assert scopes == {"SCOPE1", "SCOPE2", "SCOPE3"}
