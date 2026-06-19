"""Scheduler Health Service — M34.2 (M6).

Tracks the liveness of the background intelligence scheduler via an
in-process heartbeat. The scheduler calls record_cycle_started() /
record_cycle_completed() on each iteration; the /operations/scheduler-health
endpoint reads this state to report liveness.

State is process-local; on restart all timestamps reset to None.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class SchedulerHealthReport:
    scheduler_alive: bool
    last_cycle_started: datetime | None
    last_cycle_completed: datetime | None
    seconds_since_last_cycle: float | None
    cycles_completed: int


class _SchedulerHeartbeat:
    def __init__(self) -> None:
        self._last_cycle_started: datetime | None = None
        self._last_cycle_completed: datetime | None = None
        self._cycles_completed: int = 0
        self._alive: bool = False

    def record_started(self) -> None:
        self._alive = True
        self._last_cycle_started = datetime.now(UTC)

    def record_completed(self) -> None:
        self._last_cycle_completed = datetime.now(UTC)
        self._cycles_completed += 1

    def record_stopped(self) -> None:
        self._alive = False

    def report(self) -> SchedulerHealthReport:
        now = datetime.now(UTC)
        seconds = None
        if self._last_cycle_completed is not None:
            seconds = round((now - self._last_cycle_completed).total_seconds(), 1)
        return SchedulerHealthReport(
            scheduler_alive=self._alive,
            last_cycle_started=self._last_cycle_started,
            last_cycle_completed=self._last_cycle_completed,
            seconds_since_last_cycle=seconds,
            cycles_completed=self._cycles_completed,
        )


_heartbeat = _SchedulerHeartbeat()


def record_cycle_started() -> None:
    _heartbeat.record_started()


def record_cycle_completed() -> None:
    _heartbeat.record_completed()


def record_scheduler_stopped() -> None:
    _heartbeat.record_stopped()


def get_scheduler_health_report() -> SchedulerHealthReport:
    return _heartbeat.report()
