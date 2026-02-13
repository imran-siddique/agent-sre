"""Agent OS integration — policy signals and shadow mode hooks.

Connects to Agent OS's governance layer:
- Policy violations → SLO breaches (100% compliance SLO)
- Audit log → trace capture feed for replay
- Shadow mode → progressive delivery shadow step
- CMVK (human review) events → incident context
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_sre.incidents.detector import Signal, SignalType
from agent_sre.slo.indicators import SLI, SLIValue, TimeWindow


class PolicyComplianceSLI(SLI):
    """SLI that tracks Agent OS policy check results."""

    def __init__(self, target: float = 1.0, window: TimeWindow | str = "24h") -> None:
        super().__init__("agent_os_policy_compliance", target, window)
        self._total = 0
        self._compliant = 0

    def record_check(self, compliant: bool, policy_name: str = "", metadata: dict[str, Any] | None = None) -> SLIValue:
        self._total += 1
        if compliant:
            self._compliant += 1
        rate = self._compliant / self._total if self._total > 0 else 1.0
        return self.record(rate, {"policy_name": policy_name, **(metadata or {})})

    def collect(self) -> SLIValue:
        rate = self._compliant / self._total if self._total > 0 else 1.0
        return self.record(rate)


@dataclass
class AuditLogEntry:
    """An audit log entry from Agent OS."""

    entry_type: str  # blocked, warning, allowed, cmvk_review
    agent_id: str = ""
    action: str = ""
    policy_name: str = ""
    outcome: str = ""
    timestamp: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class AgentOSBridge:
    """Bridge between Agent OS and Agent SRE.

    Translates OS policy signals into SRE signals and SLIs.
    """

    def __init__(self) -> None:
        self._policy_sli = PolicyComplianceSLI()
        self._events_processed = 0
        self._blocked_count = 0
        self._warning_count = 0

    @property
    def policy_sli(self) -> PolicyComplianceSLI:
        return self._policy_sli

    def process_audit_entry(self, entry: AuditLogEntry) -> Signal | None:
        """Process an Agent OS audit log entry and return a Signal if relevant."""
        self._events_processed += 1

        if entry.entry_type == "blocked":
            self._blocked_count += 1
            self._policy_sli.record_check(False, entry.policy_name)
            return Signal(
                signal_type=SignalType.POLICY_VIOLATION,
                source=entry.agent_id,
                message=f"Action blocked by policy '{entry.policy_name}': {entry.action}",
                metadata=entry.details,
            )

        if entry.entry_type == "warning":
            self._warning_count += 1
            self._policy_sli.record_check(True, entry.policy_name)
            return None

        if entry.entry_type == "allowed":
            self._policy_sli.record_check(True, entry.policy_name)

        return None

    def slis(self) -> list[SLI]:
        return [self._policy_sli]

    def summary(self) -> dict[str, Any]:
        return {
            "events_processed": self._events_processed,
            "blocked_count": self._blocked_count,
            "warning_count": self._warning_count,
            "policy_compliance": self._policy_sli.current_value(),
        }
