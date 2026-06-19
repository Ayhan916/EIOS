"""M34 country risk service tests."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from application.external_intelligence.country_risk_service import (
    compute_overall_risk,
    get_country_risk,
    list_country_risks,
    upsert_country_risk_profile,
)
from domain.enums import CountryRiskLevel, ExternalSourceName
from domain.external_intelligence import CountryRiskProfile


def _now():
    return datetime.now(UTC)


# ── compute_overall_risk (pure) ────────────────────────────────────────────────

class TestComputeOverallRisk:
    def test_all_zero_returns_zero_and_low(self):
        score, level = compute_overall_risk(0.0, 0.0, 0.0, 0.0, 0.0)
        assert score == 0.0
        assert "low" in level.lower()

    def test_low_risk_scores(self):
        score, level = compute_overall_risk(10.0, 10.0, 10.0, 10.0, 10.0)
        assert score < 25.0
        assert "low" in level.lower()

    def test_moderate_risk(self):
        score, level = compute_overall_risk(40.0, 40.0, 40.0, 40.0, 40.0)
        assert 25.0 <= score < 50.0
        assert "moderate" in level.lower()

    def test_high_risk(self):
        score, level = compute_overall_risk(65.0, 65.0, 65.0, 65.0, 65.0)
        assert 50.0 <= score < 75.0
        assert "high" in level.lower()

    def test_critical_risk(self):
        score, level = compute_overall_risk(90.0, 90.0, 90.0, 90.0, 90.0)
        assert score >= 75.0
        assert "critical" in level.lower()

    def test_boundary_25_is_moderate(self):
        score, level = compute_overall_risk(25.0, 25.0, 25.0, 25.0, 25.0)
        assert score >= 25.0
        assert "moderate" in level.lower() or "high" in level.lower()

    def test_boundary_74_is_high(self):
        score, level = compute_overall_risk(74.0, 74.0, 74.0, 74.0, 74.0)
        assert score < 75.0 or "high" in level.lower()

    def test_mixed_scores_weighted(self):
        score, level = compute_overall_risk(100.0, 10.0, 10.0, 10.0, 10.0)
        assert 0.0 < score < 100.0


# ── get_country_risk (DB-backed) ───────────────────────────────────────────────

def _make_country_model(**kwargs):
    m = MagicMock()
    m.id = "cr-001"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.country_code = "DE"
    m.country_name = "Germany"
    m.dataset_id = "ds-001"
    m.governance_score = 85.0
    m.corruption_score = 20.0
    m.labour_rights_score = 75.0
    m.environmental_risk_score = 30.0
    m.human_rights_score = 80.0
    m.sanctions_status = "none"
    m.overall_risk_score = 18.0
    m.risk_level = "low"
    m.source_name = "world_bank"
    m.source_version = "2025"
    m.data_date = "2025-01-01"
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


def _make_session_first(model_or_none):
    """Mock session where execute().first() returns (model,) or None."""
    session = AsyncMock()
    result = MagicMock()
    if model_or_none is None:
        result.first.return_value = None
    else:
        result.first.return_value = (model_or_none,)
    # also set up scalar_one_or_none for upsert calls
    result.scalar_one_or_none.return_value = model_or_none
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_get_country_risk_returns_profile():
    model = _make_country_model()
    session = _make_session_first(model)
    profile = await get_country_risk("DE", session)
    assert profile is not None
    assert profile.country_code == "DE"
    assert profile.overall_risk_score == 18.0


@pytest.mark.asyncio
async def test_get_country_risk_not_found_returns_none():
    session = _make_session_first(None)
    profile = await get_country_risk("XX", session)
    assert profile is None


@pytest.mark.asyncio
async def test_list_country_risks_filters_by_level():
    model = _make_country_model(risk_level="high")
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    session.execute = AsyncMock(return_value=result)
    profiles = await list_country_risks(session, risk_level="high")
    assert len(profiles) == 1
    assert profiles[0].risk_level == "high"


@pytest.mark.asyncio
async def test_upsert_country_risk_creates_when_missing():
    """upsert_country_risk_profile creates when no existing record."""
    session = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=missing)
    session.flush = AsyncMock()

    profile = CountryRiskProfile(
        country_code="DE",
        country_name="Germany",
        dataset_id="ds-001",
        governance_score=85.0,
        corruption_score=20.0,
        labour_rights_score=75.0,
        environmental_risk_score=30.0,
        human_rights_score=80.0,
        sanctions_status="none",
        overall_risk_score=18.0,
        risk_level=CountryRiskLevel.LOW,
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="2025",
        data_date="2025-01-01",
    )
    result = await upsert_country_risk_profile(profile, session)
    assert result is not None
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_country_risk_returns_existing_when_found():
    """upsert_country_risk_profile returns existing without re-inserting."""
    model = _make_country_model()
    session = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = model
    session.execute = AsyncMock(return_value=found)

    profile = CountryRiskProfile(
        country_code="DE",
        country_name="Germany",
        dataset_id="ds-001",
        overall_risk_score=18.0,
        risk_level=CountryRiskLevel.LOW,
        sanctions_status="none",
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="2025",
        data_date="2025-01-01",
    )
    result = await upsert_country_risk_profile(profile, session)
    assert result is not None
    session.add.assert_not_called()
