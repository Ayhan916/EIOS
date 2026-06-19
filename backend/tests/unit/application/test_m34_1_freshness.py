"""M34.1 Tests — DatasetFreshnessService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.external_intelligence.freshness_service import (
    DatasetFreshness,
    assess_freshness,
    needs_refresh,
)
from domain.enums import FreshnessStatus


def _now() -> datetime:
    return datetime.now(UTC)


# ── Never-refreshed source ──────────────────────────────────────────────────


def test_never_refreshed_is_expired():
    result = assess_freshness("world_bank", last_refresh=None)
    assert result.freshness_status == FreshnessStatus.EXPIRED.value
    assert result.last_refresh is None
    assert result.hours_since_refresh is None
    assert result.hours_overdue == float("inf")


def test_never_refreshed_needs_refresh():
    result = assess_freshness("world_bank", last_refresh=None)
    assert needs_refresh(result) is True


# ── FRESH (within cadence) ──────────────────────────────────────────────────


def test_fresh_within_monthly_cadence():
    now = _now()
    last = now - timedelta(hours=10 * 24)  # 10 days ago, cadence 30 days
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert result.freshness_status == FreshnessStatus.FRESH.value
    assert result.hours_overdue == 0.0


def test_fresh_not_needs_refresh():
    now = _now()
    last = now - timedelta(hours=5 * 24)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert needs_refresh(result) is False


# ── STALE (1-2× cadence overdue) ────────────────────────────────────────────


def test_stale_between_1x_and_2x_cadence():
    now = _now()
    cadence_hours = 24 * 30
    # 35 days old → overdue by 5 days, but within 2× cadence (60 days)
    last = now - timedelta(hours=cadence_hours + 5 * 24)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert result.freshness_status == FreshnessStatus.STALE.value
    assert result.hours_overdue > 0


def test_stale_needs_refresh():
    now = _now()
    last = now - timedelta(hours=24 * 35)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert needs_refresh(result) is True


# ── EXPIRED (> 2× cadence) ──────────────────────────────────────────────────


def test_expired_beyond_2x_cadence():
    now = _now()
    # 90-day-old world_bank dataset (cadence = 30 days → expired after 60 days)
    last = now - timedelta(days=90)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert result.freshness_status == FreshnessStatus.EXPIRED.value


def test_expired_needs_refresh():
    now = _now()
    last = now - timedelta(days=90)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    assert needs_refresh(result) is True


# ── Daily cadence sources (sanctions) ───────────────────────────────────────


def test_sanctions_fresh_within_day():
    now = _now()
    last = now - timedelta(hours=12)
    result = assess_freshness("un_sanctions", last_refresh=last, as_of=now)
    assert result.freshness_status == FreshnessStatus.FRESH.value


def test_sanctions_expired_after_2_days():
    now = _now()
    last = now - timedelta(hours=50)  # > 2× daily cadence
    result = assess_freshness("un_sanctions", last_refresh=last, as_of=now)
    assert result.freshness_status == FreshnessStatus.EXPIRED.value


# ── next_expected_refresh ────────────────────────────────────────────────────


def test_next_expected_refresh_computed():
    now = _now()
    last = now - timedelta(hours=5)
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    expected = last + timedelta(hours=24 * 30)
    assert result.next_expected_refresh is not None
    diff = abs((result.next_expected_refresh - expected).total_seconds())
    assert diff < 1.0  # within 1 second


# ── Naive datetime handling ──────────────────────────────────────────────────


def test_naive_datetime_treated_as_utc():
    now = datetime.now(UTC)
    last = datetime.utcnow() - timedelta(hours=5)  # naive
    result = assess_freshness("world_bank", last_refresh=last, as_of=now)
    # Should not raise; should classify as FRESH (5h < 30-day cadence)
    assert result.freshness_status == FreshnessStatus.FRESH.value
