"""Distributed replay — multi-agent trace replay across mesh."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_sre.replay.capture import Span, SpanKind, Trace
from agent_sre.replay.engine import ReplayResult, TraceDiff, DiffType


class MeshReplayState(Enum):
    """State of a distributed replay session."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class AgentTraceRef:
    """Reference to a trace belonging to a specific agent in the mesh."""
    agent_id: str
    trace_id: str
    trace: Trace | None = None
    role: str = ""  # initiator, responder, delegate

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "trace_id": self.trace_id,
            "role": self.role,
            "span_count": len(self.trace.spans) if self.trace else 0,
        }


@dataclass
class DelegationLink:
    """A delegation link between two agents in a distributed trace."""
    from_agent: str
    to_agent: str
    from_span_id: str
    to_trace_id: str
    task_description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "from_span_id": self.from_span_id,
            "to_trace_id": self.to_trace_id,
            "task_description": self.task_description,
        }


@dataclass
class DistributedReplayResult:
    """Result of replaying a distributed multi-agent trace."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: MeshReplayState = MeshReplayState.PENDING
    agent_results: dict[str, ReplayResult] = field(default_factory=dict)
    cross_agent_diffs: list[TraceDiff] = field(default_factory=list)
    agents_completed: int = 0
    agents_total: int = 0

    @property
    def all_diffs(self) -> list[TraceDiff]:
        """All diffs across all agents."""
        diffs = list(self.cross_agent_diffs)
        for result in self.agent_results.values():
            diffs.extend(result.diffs)
        return diffs

    @property
    def success(self) -> bool:
        return self.state == MeshReplayState.COMPLETED and not self.all_diffs

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "success": self.success,
            "agents_completed": self.agents_completed,
            "agents_total": self.agents_total,
            "total_diffs": len(self.all_diffs),
            "cross_agent_diffs": [d.to_dict() for d in self.cross_agent_diffs],
            "agent_results": {
                aid: r.to_dict() for aid, r in self.agent_results.items()
            },
        }


class DistributedReplayEngine:
    """Replays multi-agent traces across mesh boundaries.

    Reconstructs the full execution flow across agents by following
    delegation spans and correlating traces from different agents.
    """

    def __init__(self) -> None:
        self._agent_traces: dict[str, AgentTraceRef] = {}
        self._delegation_links: list[DelegationLink] = []

    def add_agent_trace(self, agent_id: str, trace: Trace, role: str = "") -> None:
        """Register a trace for an agent."""
        self._agent_traces[agent_id] = AgentTraceRef(
            agent_id=agent_id,
            trace_id=trace.trace_id,
            trace=trace,
            role=role,
        )

    def link_delegation(
        self,
        from_agent: str,
        to_agent: str,
        from_span_id: str,
        to_trace_id: str,
        task_description: str = "",
    ) -> None:
        """Link a delegation span to the delegated agent's trace."""
        self._delegation_links.append(DelegationLink(
            from_agent=from_agent,
            to_agent=to_agent,
            from_span_id=from_span_id,
            to_trace_id=to_trace_id,
            task_description=task_description,
        ))

    def discover_links(self) -> list[DelegationLink]:
        """Auto-discover delegation links from spans."""
        links = []
        for ref in self._agent_traces.values():
            if ref.trace is None:
                continue
            for span in ref.trace.spans:
                if span.kind == SpanKind.DELEGATION:
                    target_agent = span.attributes.get("target_agent", "")
                    target_trace = span.attributes.get("target_trace_id", "")
                    if target_agent and target_agent in self._agent_traces:
                        link = DelegationLink(
                            from_agent=ref.agent_id,
                            to_agent=target_agent,
                            from_span_id=span.span_id,
                            to_trace_id=target_trace or (
                                self._agent_traces[target_agent].trace_id
                                if self._agent_traces[target_agent].trace else ""
                            ),
                            task_description=span.name,
                        )
                        links.append(link)
                        self._delegation_links.append(link)
        return links

    def replay(self) -> DistributedReplayResult:
        """Replay all agent traces and check cross-agent consistency."""
        from agent_sre.replay.engine import ReplayEngine

        result = DistributedReplayResult(
            agents_total=len(self._agent_traces),
        )
        result.state = MeshReplayState.RUNNING

        engine = ReplayEngine()

        for agent_id, ref in self._agent_traces.items():
            if ref.trace is None:
                continue
            agent_result = engine.replay(ref.trace)
            result.agent_results[agent_id] = agent_result
            result.agents_completed += 1

        # Check cross-agent consistency
        result.cross_agent_diffs = self._check_cross_agent(result)

        if result.agents_completed == result.agents_total:
            result.state = MeshReplayState.COMPLETED
        elif result.agents_completed > 0:
            result.state = MeshReplayState.PARTIAL
        else:
            result.state = MeshReplayState.FAILED

        return result

    def _check_cross_agent(self, result: DistributedReplayResult) -> list[TraceDiff]:
        """Check consistency across delegation boundaries."""
        diffs: list[TraceDiff] = []

        for link in self._delegation_links:
            from_ref = self._agent_traces.get(link.from_agent)
            to_ref = self._agent_traces.get(link.to_agent)

            if not from_ref or not from_ref.trace or not to_ref or not to_ref.trace:
                diffs.append(TraceDiff(
                    diff_type=DiffType.MISSING_SPAN,
                    span_name=f"delegation:{link.from_agent}->{link.to_agent}",
                    description=f"Missing trace for delegation from {link.from_agent} to {link.to_agent}",
                ))
                continue

            # Find the delegation span output and compare with delegate's actual output
            delegation_span = None
            for s in from_ref.trace.spans:
                if s.span_id == link.from_span_id:
                    delegation_span = s
                    break

            if delegation_span and to_ref.trace.task_output is not None:
                expected = delegation_span.output_data.get("result")
                actual = to_ref.trace.task_output
                if expected and actual and str(expected) != str(actual):
                    diffs.append(TraceDiff(
                        diff_type=DiffType.OUTPUT_MISMATCH,
                        span_name=f"delegation:{link.from_agent}->{link.to_agent}",
                        original=expected,
                        replayed=actual,
                        description=f"Delegation output mismatch: {link.from_agent} expected different result from {link.to_agent}",
                    ))

        return diffs

    def execution_order(self) -> list[str]:
        """Get the execution order of agents based on delegation links."""
        order: list[str] = []
        visited: set[str] = set()

        initiators = set(self._agent_traces.keys())
        for link in self._delegation_links:
            initiators.discard(link.to_agent)

        def _visit(agent_id: str) -> None:
            if agent_id in visited:
                return
            visited.add(agent_id)
            order.append(agent_id)
            for link in self._delegation_links:
                if link.from_agent == agent_id:
                    _visit(link.to_agent)

        for init in initiators:
            _visit(init)

        # Add any unvisited
        for aid in self._agent_traces:
            if aid not in visited:
                order.append(aid)

        return order

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": {aid: ref.to_dict() for aid, ref in self._agent_traces.items()},
            "delegation_links": [l.to_dict() for l in self._delegation_links],
            "execution_order": self.execution_order(),
        }
