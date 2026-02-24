# Community Edition — basic implementation
"""Chaos experiment library — pre-built resilience test scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_sre.chaos.engine import (
    AbortCondition,
    ChaosExperiment,
    Fault,
)


@dataclass
class ExperimentTemplate:
    """A reusable chaos experiment template."""
    template_id: str
    name: str
    description: str
    category: str  # tool, llm, network, cost, agent
    severity: str = "medium"  # low, medium, high, critical
    faults: list[Fault] = field(default_factory=list)
    abort_conditions: list[AbortCondition] = field(default_factory=list)
    duration_seconds: int = 1800
    blast_radius: float = 1.0
    tags: list[str] = field(default_factory=list)

    def instantiate(self, target_agent: str, **overrides: Any) -> ChaosExperiment:
        """Create a concrete experiment from this template."""
        return ChaosExperiment(
            name=overrides.get("name", self.name),
            target_agent=target_agent,
            faults=self.faults,
            duration_seconds=overrides.get("duration_seconds", self.duration_seconds),
            abort_conditions=self.abort_conditions,
            blast_radius=overrides.get("blast_radius", self.blast_radius),
            description=self.description,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "fault_count": len(self.faults),
            "duration_seconds": self.duration_seconds,
            "blast_radius": self.blast_radius,
            "tags": self.tags,
        }


class ChaosLibrary:
    """Library of pre-built chaos experiment templates.

    Provides ready-to-use experiments for common failure scenarios
    in multi-agent systems.
    """

    def __init__(self) -> None:
        self._templates: dict[str, ExperimentTemplate] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """Load built-in experiment templates (3 basic fault types)."""
        builtins = [
            ExperimentTemplate(
                template_id="timeout-injection",
                name="Timeout Injection",
                description="Tests agent behavior when tools take too long to respond.",
                category="tool",
                severity="medium",
                faults=[Fault.timeout_injection("*", delay_ms=30000, rate=0.5)],
                abort_conditions=[AbortCondition("task_success_rate", 0.5, "lte")],
                duration_seconds=1800,
                tags=["tool", "timeout", "latency"],
            ),
            ExperimentTemplate(
                template_id="error-injection",
                name="Error Injection",
                description="Simulates a burst of errors to test error handling.",
                category="tool",
                severity="high",
                faults=[Fault.error_injection("*", error="internal_server_error", rate=0.8)],
                abort_conditions=[AbortCondition("task_success_rate", 0.3, "lte")],
                duration_seconds=900,
                blast_radius=0.5,
                tags=["tool", "error", "resilience"],
            ),
            ExperimentTemplate(
                template_id="latency-injection",
                name="Latency Injection",
                description="Simulates provider latency spikes.",
                category="llm",
                severity="medium",
                faults=[Fault.latency_injection("*", delay_ms=15000, rate=0.4)],
                abort_conditions=[AbortCondition("task_success_rate", 0.7, "lte")],
                duration_seconds=3600,
                tags=["llm", "latency", "provider"],
            ),
        ]
        for template in builtins:
            self._templates[template.template_id] = template

    def register(self, template: ExperimentTemplate) -> None:
        """Register a custom experiment template."""
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> ExperimentTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: str | None = None,
        severity: str | None = None,
        tag: str | None = None,
    ) -> list[ExperimentTemplate]:
        """List templates with optional filtering."""
        result = list(self._templates.values())
        if category:
            result = [t for t in result if t.category == category]
        if severity:
            result = [t for t in result if t.severity == severity]
        if tag:
            result = [t for t in result if tag in t.tags]
        return result

    def instantiate(self, template_id: str, target_agent: str, **overrides: Any) -> ChaosExperiment | None:
        """Create a concrete experiment from a template."""
        template = self.get(template_id)
        if template is None:
            return None
        return template.instantiate(target_agent, **overrides)

    def categories(self) -> list[str]:
        """List all template categories."""
        return sorted(set(t.category for t in self._templates.values()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_count": len(self._templates),
            "categories": self.categories(),
            "templates": [t.to_dict() for t in self._templates.values()],
        }
