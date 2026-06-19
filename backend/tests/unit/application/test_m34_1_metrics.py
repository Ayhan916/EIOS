"""M34.1 Tests — External Intelligence Metrics (_ExtCounters)."""

from __future__ import annotations

import pytest

from application.external_intelligence.metrics import _ExtCounters


def _counters() -> _ExtCounters:
    return _ExtCounters()


# ── dataset_refresh_total ────────────────────────────────────────────────────


def test_record_refresh_increments_total():
    c = _counters()
    c.record_dataset_refresh("world_bank", success=True)
    assert c.dataset_refresh_total == 1


def test_record_refresh_success_not_failed():
    c = _counters()
    c.record_dataset_refresh("world_bank", success=True)
    assert c.dataset_refresh_failed_total == 0


def test_record_refresh_failure_increments_failed():
    c = _counters()
    c.record_dataset_refresh("world_bank", success=False)
    assert c.dataset_refresh_total == 1
    assert c.dataset_refresh_failed_total == 1


# ── connector_failures ───────────────────────────────────────────────────────


def test_record_connector_failure():
    # M4: record_connector_failure only tracks per-connector count;
    # dataset_refresh_failed_total is incremented by record_dataset_refresh(success=False)
    c = _counters()
    c.record_connector_failure("un_sanctions")
    assert c.connector_failures("un_sanctions") == 1
    assert c.dataset_refresh_failed_total == 0  # M4 fix: no longer double-incremented


def test_connector_failures_independent():
    c = _counters()
    c.record_connector_failure("un_sanctions")
    c.record_connector_failure("eu_sanctions")
    assert c.connector_failures("un_sanctions") == 1
    assert c.connector_failures("eu_sanctions") == 1
    assert c.connector_failures("world_bank") == 0  # not recorded


# ── connector_runtime ────────────────────────────────────────────────────────


def test_record_connector_runtime():
    c = _counters()
    c.record_connector_runtime("world_bank", 10.0)
    c.record_connector_runtime("world_bank", 20.0)
    assert c.connector_avg_runtime("world_bank") == pytest.approx(15.0)


def test_connector_avg_runtime_zero_when_none():
    c = _counters()
    assert c.connector_avg_runtime("world_bank") == 0.0


# ── sanctions_updates_total ──────────────────────────────────────────────────


def test_record_sanctions_update():
    c = _counters()
    c.record_sanctions_update()
    c.record_sanctions_update()
    assert c.sanctions_updates_total == 2


# ── benchmark_refresh_total ──────────────────────────────────────────────────


def test_record_benchmark_refresh():
    c = _counters()
    c.record_benchmark_refresh()
    assert c.benchmark_refresh_total == 1


# ── validation failure ───────────────────────────────────────────────────────


def test_record_validation_failure_not_quarantined():
    c = _counters()
    c.record_validation_failure(quarantined=False)
    assert c.dataset_validation_failures == 1
    assert c.dataset_quarantined_total == 0


def test_record_validation_failure_quarantined():
    c = _counters()
    c.record_validation_failure(quarantined=True)
    assert c.dataset_validation_failures == 1
    assert c.dataset_quarantined_total == 1


# ── to_prometheus_lines ──────────────────────────────────────────────────────


def test_prometheus_lines_contain_refresh_counter():
    c = _counters()
    c.record_dataset_refresh("world_bank", success=True)
    lines = "\n".join(c.to_prometheus_lines("test"))
    assert "eios_external_dataset_refresh_total" in lines
    assert "1" in lines


def test_prometheus_lines_contain_sanctions_counter():
    c = _counters()
    c.record_sanctions_update()
    lines = "\n".join(c.to_prometheus_lines("prod"))
    assert "eios_sanctions_updates_total" in lines
    assert "1" in lines


def test_prometheus_lines_per_connector():
    c = _counters()
    c.record_connector_failure("un_sanctions")
    c.record_connector_runtime("un_sanctions", 5.0)
    lines = "\n".join(c.to_prometheus_lines("staging"))
    assert "eios_connector_failures_total" in lines
    assert "un_sanctions" in lines


def test_prometheus_lines_empty_counters():
    c = _counters()
    lines = "\n".join(c.to_prometheus_lines("dev"))
    assert "eios_external_dataset_refresh_total" in lines
    # All counters zero
    assert "} 0" in lines


def test_all_connectors_returns_seen_names():
    c = _counters()
    c.record_dataset_refresh("world_bank", success=True)
    c.record_connector_failure("un_sanctions")
    names = c.all_connectors()
    assert "world_bank" in names
    assert "un_sanctions" in names
