"""Chaos engine — fault injection and resilience testing for agents."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FaultType(Enum):
    """Types of faults that can be injected."""

    TOOL_TIMEOUT = "tool_timeout"
    TOOL_ERROR = "tool_error"
    TOOL_WRONG_SCHEMA = "tool_wrong_schema"
    LLM_LATENCY = "llm_latency"
    LLM_DEGRADED = "llm_degraded"
    DELEGATION_REJECT = "delegation_reject"
    CREDENTIAL_EXPIRE = "credential_expire"
    NETWORK_PARTITION = "network_partition"
    COST_SPIKE = "cost_spike"


class ExperimentState(Enum):
    """State of a chaos experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


@dataclass
class Fault:
    """A fault to inject during a chaos experiment."""

    fault_type: FaultType
    target: str  # tool name, agent ID, provider name
    rate: float = 1.0  # Fraction of calls affected (0.0-1.0)
    params: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def tool_timeout(tool: str, delay_ms: int = 30000, rate: float = 1.0) -> Fault:
        return Fault(FaultType.TOOL_TIMEOUT, tool, rate, {"delay_ms": delay_ms})

    @staticmethod
    def tool_error(tool: str, error: str = "internal_error", rate: float = 1.0) -> Fault:
        return Fault(FaultType.TOOL_ERROR, tool, rate, {"error": error})

    @staticmethod
    def tool_wrong_schema(tool: str, rate: float = 1.0) -> Fault:
        return Fault(FaultType.TOOL_WRONG_SCHEMA, tool, rate, {})

    @staticmethod
    def llm_latency(provider: str, p99_ms: int = 15000, rate: float = 1.0) -> Fault:
        return Fault(FaultType.LLM_LATENCY, provider, rate, {"p99_ms": p99_ms})

    @staticmethod
    def llm_degraded(provider: str, quality: float = 0.5, rate: float = 1.0) -> Fault:
        return Fault(FaultType.LLM_DEGRADED, provider, rate, {"quality": quality})

    @staticmethod
    def delegation_reject(from_agent: str, rate: float = 0.1) -> Fault:
        return Fault(FaultType.DELEGATION_REJECT, from_agent, rate, {})

    @staticmethod
    def credential_expire(agent: str) -> Fault:
        return Fault(FaultType.CREDENTIAL_EXPIRE, agent, 1.0, {})

    @staticmethod
    def network_partition(agents: list[str]) -> Fault:
        return Fault(FaultType.NETWORK_PARTITION, ",".join(agents), 1.0, {"agents": agents})

    @staticmethod
    def cost_spike(tool: str, multiplier: float = 10.0) -> Fault:
        return Fault(FaultType.COST_SPIKE, tool, 1.0, {"multiplier": multiplier})

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_type": self.fault_type.value,
            "target": self.target,
            "rate": self.rate,
            "params": self.params,
        }


@dataclass
class AbortCondition:
    """Condition that stops a chaos experiment for safety."""

    metric: str
    threshold: float
    comparator: str = "lte"  # abort when metric drops below threshold

    def should_abort(self, value: float) -> bool:
        if self.comparator == "lte":
            return value <= self.threshold
        elif self.comparator == "gte":
            return value >= self.threshold
        return False

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "threshold": self.threshold, "comparator": self.comparator}


@dataclass
class FaultInjectionEvent:
    """Record of a fault being injected."""

    fault_type: FaultType
    target: str
    timestamp: float = field(default_factory=time.time)
    applied: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_type": self.fault_type.value,
            "target": self.target,
            "timestamp": self.timestamp,
            "applied": self.applied,
            "details": self.details,
        }


@dataclass
class ResilienceScore:
    """Resilience score from a chaos experiment."""

    overall: float = 0.0  # 0-100
    fault_tolerance: float = 0.0  # How well agent handled faults
    recovery_time_ms: float = 0.0  # Time to recover after fault
    degradation_percent: float = 0.0  # Quality degradation during fault
    cost_impact_percent: float = 0.0  # Cost increase during fault

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "fault_tolerance": self.fault_tolerance,
            "recovery_time_ms": self.recovery_time_ms,
            "degradation_percent": self.degradation_percent,
            "cost_impact_percent": self.cost_impact_percent,
        }


class ChaosExperiment:
    """A chaos engineering experiment against agent(s)."""

    def __init__(
        self,
        name: str,
        target_agent: str,
        faults: list[Fault],
        duration_seconds: int = 1800,
        abort_conditions: list[AbortCondition] | None = None,
        blast_radius: float = 1.0,
        description: str = "",
    ) -> None:
        self.experiment_id = uuid.uuid4().hex[:12]
        self.name = name
        self.target_agent = target_agent
        self.faults = faults
        self.duration_seconds = duration_seconds
        self.abort_conditions = abort_conditions or []
        self.blast_radius = min(max(blast_radius, 0.0), 1.0)
        self.description = description
        self.state = ExperimentState.PENDING
        self.injection_events: list[FaultInjectionEvent] = []
        self.started_at: float | None = None
        self.ended_at: float | None = None
        self.abort_reason: str | None = None
        self.resilience: ResilienceScore = ResilienceScore()

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at or time.time()
        return end - self.started_at

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.duration_seconds - self.elapsed_seconds)

    @property
    def is_expired(self) -> bool:
        return self.elapsed_seconds >= self.duration_seconds

    def start(self) -> None:
        """Start the experiment."""
        self.state = ExperimentState.RUNNING
        self.started_at = time.time()

    def inject_fault(self, fault: Fault, applied: bool = True, details: dict[str, Any] | None = None) -> None:
        """Record a fault injection event."""
        self.injection_events.append(FaultInjectionEvent(
            fault_type=fault.fault_type,
            target=fault.target,
            applied=applied,
            details=details or fault.params,
        ))

    def check_abort(self, metrics: dict[str, float]) -> bool:
        """Check abort conditions. Returns True if experiment should stop."""
        for condition in self.abort_conditions:
            value = metrics.get(condition.metric)
            if value is not None and condition.should_abort(value):
                self.abort(reason=f"{condition.metric} = {value} (threshold: {condition.threshold})")
                return True
        return False

    def abort(self, reason: str = "") -> None:
        """Abort the experiment."""
        self.state = ExperimentState.ABORTED
        self.ended_at = time.time()
        self.abort_reason = reason

    def complete(self, resilience: ResilienceScore | None = None) -> None:
        """Mark the experiment as completed."""
        self.state = ExperimentState.COMPLETED
        self.ended_at = time.time()
        if resilience:
            self.resilience = resilience

    def calculate_resilience(
        self,
        baseline_success_rate: float,
        experiment_success_rate: float,
        recovery_time_ms: float = 0.0,
        cost_increase_percent: float = 0.0,
    ) -> ResilienceScore:
        """Calculate resilience score from experiment metrics."""
        if baseline_success_rate > 0:
            fault_tolerance = experiment_success_rate / baseline_success_rate * 100
        else:
            fault_tolerance = 0.0

        degradation = max(0.0, (1 - experiment_success_rate / max(baseline_success_rate, 0.001)) * 100)

        overall = max(0.0, min(100.0,
            fault_tolerance * 0.4
            + max(0.0, 100 - recovery_time_ms / 100) * 0.3
            + max(0.0, 100 - degradation) * 0.2
            + max(0.0, 100 - cost_increase_percent) * 0.1
        ))

        self.resilience = ResilienceScore(
            overall=round(overall, 1),
            fault_tolerance=round(fault_tolerance, 1),
            recovery_time_ms=recovery_time_ms,
            degradation_percent=round(degradation, 1),
            cost_impact_percent=round(cost_increase_percent, 1),
        )
        return self.resilience

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "target_agent": self.target_agent,
            "state": self.state.value,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "blast_radius": self.blast_radius,
            "faults": [f.to_dict() for f in self.faults],
            "abort_conditions": [a.to_dict() for a in self.abort_conditions],
            "injection_count": len(self.injection_events),
            "abort_reason": self.abort_reason,
            "resilience": self.resilience.to_dict(),
        }
