"""SLO definitions and Error Budget engine."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_sre.slo.indicators import SLI


class ExhaustionAction(Enum):
    """What to do when error budget is exhausted."""

    ALERT = "alert"
    FREEZE_DEPLOYMENTS = "freeze_deployments"
    CIRCUIT_BREAK = "circuit_break"
    THROTTLE = "throttle"


@dataclass
class BurnRateAlert:
    """A burn rate alert threshold."""

    name: str
    rate: float
    severity: str = "warning"  # warning, critical, page
    window_seconds: int = 3600  # 1h fast burn by default

    def is_firing(self, current_burn_rate: float) -> bool:
        """Check if this alert should fire."""
        return current_burn_rate >= self.rate


@dataclass
class ErrorBudget:
    """Tracks error budget consumption for an SLO.

    Error Budget = 1 - SLO target
    Burn Rate = actual error rate / allowed error rate
    """

    total: float = 0.0  # Set from SLO target
    consumed: float = 0.0
    window_seconds: int = 2592000  # 30 days default
    burn_rate_alert: float = 2.0
    burn_rate_critical: float = 10.0
    exhaustion_action: ExhaustionAction = ExhaustionAction.ALERT
    _events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def remaining(self) -> float:
        """Remaining error budget as a fraction (0.0 to 1.0)."""
        if self.total <= 0:
            return 0.0
        return max(0.0, 1.0 - (self.consumed / self.total))

    @property
    def remaining_percent(self) -> float:
        """Remaining error budget as percentage."""
        return self.remaining * 100.0

    @property
    def is_exhausted(self) -> bool:
        """True if error budget is fully consumed."""
        return self.consumed >= self.total

    def record_event(self, good: bool) -> None:
        """Record a good or bad event against the budget."""
        if not good:
            self.consumed += 1.0
        self._events.append({"good": good, "timestamp": time.time()})

    def burn_rate(self, window_seconds: int | None = None) -> float:
        """Calculate current burn rate within a time window.

        Burn rate = (actual errors in window / window size) / (budget / total window)
        A burn rate of 1.0 means consuming budget at exactly the expected rate.
        >1.0 means faster than expected.
        """
        window = window_seconds or 3600  # Default 1h window
        cutoff = time.time() - window
        recent_events = [e for e in self._events if e["timestamp"] >= cutoff]
        if not recent_events:
            return 0.0

        errors_in_window = sum(1 for e in recent_events if not e["good"])
        total_in_window = len(recent_events)

        if total_in_window == 0 or self.total <= 0:
            return 0.0

        actual_error_rate = errors_in_window / total_in_window
        allowed_error_rate = self.total / max(self.window_seconds, 1)
        if allowed_error_rate <= 0:
            return float("inf") if errors_in_window > 0 else 0.0

        return actual_error_rate / allowed_error_rate

    def alerts(self) -> list[BurnRateAlert]:
        """Get default burn rate alerts."""
        return [
            BurnRateAlert("fast_burn_warning", self.burn_rate_alert, "warning", 3600),
            BurnRateAlert("fast_burn_critical", self.burn_rate_critical, "critical", 3600),
            BurnRateAlert("slow_burn_warning", self.burn_rate_alert / 2, "warning", 21600),
        ]

    def firing_alerts(self) -> list[BurnRateAlert]:
        """Get alerts that are currently firing."""
        current = self.burn_rate()
        return [a for a in self.alerts() if a.is_firing(current)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total": self.total,
            "consumed": self.consumed,
            "remaining_percent": self.remaining_percent,
            "is_exhausted": self.is_exhausted,
            "burn_rate_1h": self.burn_rate(3600),
            "burn_rate_6h": self.burn_rate(21600),
            "exhaustion_action": self.exhaustion_action.value,
            "firing_alerts": [a.name for a in self.firing_alerts()],
        }


class SLOStatus(Enum):
    """Current SLO health status."""

    HEALTHY = "healthy"  # Within budget, no alerts
    WARNING = "warning"  # Burn rate elevated
    CRITICAL = "critical"  # Burn rate critical, budget at risk
    EXHAUSTED = "exhausted"  # Budget consumed
    UNKNOWN = "unknown"  # Not enough data


class SLO:
    """Service Level Objective for an AI agent.

    Combines multiple SLIs with targets and an error budget to define
    what "reliable" means for this agent.
    """

    def __init__(
        self,
        name: str,
        indicators: list[SLI],
        error_budget: ErrorBudget | None = None,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.indicators = indicators
        self.description = description
        self.labels = labels or {}

        # Calculate total error budget from strictest indicator
        if error_budget is None:
            self.error_budget = ErrorBudget()
        else:
            self.error_budget = error_budget

        if self.error_budget.total == 0 and indicators:
            min_target = min(sli.target for sli in indicators)
            self.error_budget.total = 1.0 - min_target

        self._created_at = time.time()

    def evaluate(self) -> SLOStatus:
        """Evaluate current SLO status."""
        if self.error_budget.is_exhausted:
            return SLOStatus.EXHAUSTED

        firing = self.error_budget.firing_alerts()
        if any(a.severity == "critical" for a in firing):
            return SLOStatus.CRITICAL
        if any(a.severity == "warning" for a in firing):
            return SLOStatus.WARNING

        # Check if we have enough data
        has_data = any(sli.current_value() is not None for sli in self.indicators)
        if not has_data:
            return SLOStatus.UNKNOWN

        return SLOStatus.HEALTHY

    def record_event(self, good: bool) -> None:
        """Record a good or bad event against the SLO."""
        self.error_budget.record_event(good)

    def indicator_summary(self) -> list[dict[str, Any]]:
        """Get summary of all indicators."""
        return [sli.to_dict() for sli in self.indicators]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.evaluate().value,
            "labels": self.labels,
            "error_budget": self.error_budget.to_dict(),
            "indicators": self.indicator_summary(),
        }

    def __repr__(self) -> str:
        status = self.evaluate().value
        remaining = self.error_budget.remaining_percent
        return f"SLO(name={self.name!r}, status={status}, budget={remaining:.1f}%)"
