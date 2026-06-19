"""M34.2 Tests — M4 metrics counter correctness."""

from __future__ import annotations

from application.external_intelligence.metrics import _ExtCounters


def _fresh_counters() -> _ExtCounters:
    return _ExtCounters()


def test_record_dataset_refresh_success_increments_total():
    c = _fresh_counters()
    c.record_dataset_refresh("world_bank", success=True)
    assert c.dataset_refresh_total == 1
    assert c.dataset_refresh_failed_total == 0


def test_record_dataset_refresh_failure_increments_both():
    """M4: failure must also increment dataset_refresh_total."""
    c = _fresh_counters()
    c.record_dataset_refresh("world_bank", success=False)
    assert c.dataset_refresh_total == 1
    assert c.dataset_refresh_failed_total == 1


def test_failed_total_never_exceeds_total():
    """M4: failed_total must never exceed total."""
    c = _fresh_counters()
    c.record_dataset_refresh("world_bank", success=True)
    c.record_dataset_refresh("world_bank", success=False)
    c.record_dataset_refresh("un_sanctions", success=False)
    assert c.dataset_refresh_total == 3
    assert c.dataset_refresh_failed_total == 2
    assert c.dataset_refresh_failed_total <= c.dataset_refresh_total


def test_record_connector_failure_does_not_double_count_failed_total():
    """M4: record_connector_failure only increments per-connector counter."""
    c = _fresh_counters()
    c.record_dataset_refresh("world_bank", success=False)
    c.record_connector_failure("world_bank")
    # dataset_refresh_failed_total must still be 1 (not 2)
    assert c.dataset_refresh_failed_total == 1


def test_connector_failure_count_tracked_separately():
    c = _fresh_counters()
    c.record_connector_failure("world_bank")
    c.record_connector_failure("world_bank")
    assert c.connector_failures("world_bank") == 2


def test_record_connector_runtime_accumulates():
    c = _fresh_counters()
    c.record_connector_runtime("world_bank", 5.0)
    c.record_connector_runtime("world_bank", 3.0)
    assert c.connector_avg_runtime("world_bank") == 4.0


def test_prometheus_lines_include_all_m34_metrics():
    c = _fresh_counters()
    c.record_dataset_refresh("world_bank", success=True)
    lines = "\n".join(c.to_prometheus_lines("test"))
    assert "eios_external_dataset_refresh_total" in lines
    assert "eios_external_dataset_refresh_failed_total" in lines
    assert "eios_sanctions_updates_total" in lines
    assert "eios_benchmark_refresh_total" in lines
