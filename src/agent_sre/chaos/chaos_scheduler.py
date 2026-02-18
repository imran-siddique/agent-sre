"""Chaos scheduler — cron-based execution with blackouts and progressive severity."""

from __future__ import annotations

from datetime import datetime, timezone

from croniter import croniter

from agent_sre.chaos.scheduler import (
    ChaosSchedule,
    ScheduleExecution,
)


class ChaosScheduler:
    """Manages chaos experiment schedules, blackouts, and progressive severity."""

    def __init__(self, schedules: list[ChaosSchedule] | None = None) -> None:
        self._schedules: dict[str, ChaosSchedule] = {
            s.id: s for s in (schedules or [])
        }
        self._executions: dict[str, list[ScheduleExecution]] = {}

    def should_run(self, schedule_id: str, now: datetime | None = None) -> bool:
        """Check if a schedule should fire now (enabled, matches cron, not in blackout)."""
        schedule = self._schedules.get(schedule_id)
        if schedule is None or not schedule.enabled:
            return False

        now = now or datetime.now(tz=timezone.utc)
        if self.is_in_blackout(schedule, now):
            return False

        return _cron_matches(schedule.cron_expression, now)

    def get_due_schedules(self, now: datetime | None = None) -> list[ChaosSchedule]:
        """Return all schedules that are due to run at the given time."""
        now = now or datetime.now(tz=timezone.utc)
        return [
            s for s in self._schedules.values()
            if self.should_run(s.id, now)
        ]

    def is_in_blackout(self, schedule: ChaosSchedule, now: datetime | None = None) -> bool:
        """Check if the schedule is currently in a blackout window."""
        now = now or datetime.now(tz=timezone.utc)
        return any(bw.contains(now) for bw in schedule.blackout_windows)

    def get_current_severity(self, schedule_id: str) -> float:
        """Compute current severity based on progressive config and execution history."""
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return 0.0

        config = schedule.progressive_config
        if config is None:
            return 1.0

        history = self._executions.get(schedule_id, [])
        consecutive_successes = 0
        for ex in reversed(history):
            if ex.result == "pass":
                consecutive_successes += 1
            else:
                break

        steps = consecutive_successes // config.increase_after_success_count
        severity = config.initial_severity + steps * config.step_increase
        return min(severity, config.max_severity)

    def record_execution(self, execution: ScheduleExecution) -> None:
        """Record an execution result and update progressive state."""
        self._executions.setdefault(execution.schedule_id, []).append(execution)

    def get_resilience_trend(self, schedule_id: str, window: int = 10) -> list[float]:
        """Return the last N resilience scores for a schedule."""
        history = self._executions.get(schedule_id, [])
        return [ex.resilience_score for ex in history[-window:]]


def _cron_matches(expression: str, now: datetime) -> bool:
    """Check if a cron expression matches the given minute."""
    truncated = now.replace(second=0, microsecond=0)
    return croniter.match(expression, truncated)  # type: ignore[no-any-return]
