"""M34.2 Tests — M6 Scheduler Health Service."""

from __future__ import annotations

from application.external_intelligence.scheduler_health import (
    _SchedulerHeartbeat,
    get_scheduler_health_report,
)


def _fresh_heartbeat() -> _SchedulerHeartbeat:
    return _SchedulerHeartbeat()


def test_initial_state_not_alive():
    hb = _fresh_heartbeat()
    report = hb.report()
    assert report.scheduler_alive is False
    assert report.last_cycle_started is None
    assert report.last_cycle_completed is None
    assert report.cycles_completed == 0
    assert report.seconds_since_last_cycle is None


def test_record_started_marks_alive():
    hb = _fresh_heartbeat()
    hb.record_started()
    report = hb.report()
    assert report.scheduler_alive is True
    assert report.last_cycle_started is not None


def test_record_completed_increments_count():
    hb = _fresh_heartbeat()
    hb.record_started()
    hb.record_completed()
    report = hb.report()
    assert report.cycles_completed == 1
    assert report.last_cycle_completed is not None


def test_record_stopped_marks_not_alive():
    hb = _fresh_heartbeat()
    hb.record_started()
    hb.record_completed()
    hb.record_stopped()
    report = hb.report()
    assert report.scheduler_alive is False


def test_cycles_count_accumulates():
    hb = _fresh_heartbeat()
    for _ in range(5):
        hb.record_started()
        hb.record_completed()
    report = hb.report()
    assert report.cycles_completed == 5


def test_seconds_since_last_cycle_non_negative():
    hb = _fresh_heartbeat()
    hb.record_started()
    hb.record_completed()
    report = hb.report()
    assert report.seconds_since_last_cycle is not None
    assert report.seconds_since_last_cycle >= 0.0


def test_get_scheduler_health_report_returns_report():
    report = get_scheduler_health_report()
    assert hasattr(report, "scheduler_alive")
    assert hasattr(report, "cycles_completed")
    assert hasattr(report, "seconds_since_last_cycle")
