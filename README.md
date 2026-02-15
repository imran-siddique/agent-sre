# Agent SRE

**Reliability Engineering for AI Agent Systems**

> SRE practices adapted for multi-agent production environments. Not agents *doing* SRE — SRE *for* agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Quickstart

```bash
pip install agent-sre
```

```python
from agent_sre import SLO, ErrorBudget
from agent_sre.slo.indicators import TaskSuccessRate, CostPerTask, HallucinationRate

slo = SLO(
    name="my-agent",
    indicators=[
        TaskSuccessRate(target=0.95, window="24h"),
        CostPerTask(target_usd=0.50, window="24h"),
        HallucinationRate(target=0.05, window="24h"),
    ],
    error_budget=ErrorBudget(total=0.05),
)

# After each agent task
slo.indicators[0].record_task(success=True)
slo.indicators[1].record_cost(cost_usd=0.35)
slo.indicators[2].record_evaluation(hallucinated=False)
slo.record_event(good=True)

# Check health
status = slo.evaluate()  # HEALTHY, WARNING, CRITICAL, or EXHAUSTED
```

See [examples/](examples/) for complete runnable demos: SLO monitoring, cost guardrails, canary deployments, chaos testing.

---

## The Problem

AI agents in production fail differently than traditional services:

- **Non-deterministic failures** — Same input, different output, no stack trace
- **Silent reasoning errors** — Agent returns "success" but the answer is wrong
- **Cascading delegation failures** — Agent A trusts Agent B who calls Agent C which hallucinates
- **Tool invocation drift** — MCP server schema changes silently break agent workflows
- **Cost explosions** — Runaway tool loops burn $10K before anyone notices

Traditional monitoring catches crashes. Agent SRE catches *everything else*.

## How It Works

Agent SRE brings Site Reliability Engineering principles — SLOs, error budgets, progressive delivery, chaos testing — to multi-agent AI systems. It integrates with [Agent OS](https://github.com/imran-siddique/agent-os) (kernel-level governance) and [Agent Mesh](https://github.com/imran-siddique/agent-mesh) (distributed identity and trust) to provide end-to-end reliability across the full agent lifecycle.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your AI Agents                               │
├─────────────────────────────────────────────────────────────────┤
│  Agent SRE                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ SLO Engine   │ │ Replay       │ │ Progressive Delivery     │ │
│  │              │ │ Engine       │ │                          │ │
│  │ • Define     │ │              │ │ • Shadow testing         │ │
│  │ • Measure    │ │ • Capture    │ │ • Canary rollouts        │ │
│  │ • Alert      │ │ • Replay     │ │ • Automated rollback     │ │
│  │ • Budget     │ │ • Compare    │ │ • Traffic splitting      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Chaos        │ │ Cost         │ │ Incident                 │ │
│  │ Engine       │ │ Guard        │ │ Manager                  │ │
│  │              │ │              │ │                          │ │
│  │ • Fault      │ │ • Per-agent  │ │ • Auto-detection         │ │
│  │   injection  │ │   budgets    │ │ • Root cause analysis    │ │
│  │ • Latency    │ │ • Anomaly    │ │ • Postmortem generation  │ │
│  │ • Tool fail  │ │   detection  │ │ • Runbook execution      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Agent Mesh — Identity, Trust, Routing                          │
├─────────────────────────────────────────────────────────────────┤
│  Agent OS — Policy Enforcement, Audit, Compliance               │
└─────────────────────────────────────────────────────────────────┘
```

## Core Capabilities

### 1. SLO Engine — Define What "Reliable" Means for Agents

Traditional SRE defines SLOs for services (99.9% uptime). Agent SRE defines SLOs for *agent behavior*:

| SLI (Indicator) | Example SLO | Error Budget |
|---|---|---|
| **Task Success Rate** | 99.5% of tasks complete correctly | 5 failures per 1,000 |
| **Tool Call Accuracy** | 99.9% correct tool selection | 1 wrong tool per 1,000 |
| **Response Latency (P95)** | < 5s for single-step, < 30s for multi-step | Measured per window |
| **Cost Per Task** | < $0.50 per task (mean) | Alert at 2x baseline |
| **Policy Compliance** | 100% adherence to Agent OS policies | Zero tolerance |
| **Delegation Chain Depth** | ≤ 3 hops for any request | Hard limit |
| **Hallucination Rate** | < 1% factual errors in outputs | Measured by evaluators |

```python
from agent_sre import SLO, ErrorBudget
from agent_sre.slo.indicators import TaskSuccessRate, CostPerTask, HallucinationRate

slo = SLO(
    name="customer-support-agent",
    indicators=[
        TaskSuccessRate(target=0.995, window="30d"),
        CostPerTask(target_usd=0.50, window="24h"),
        HallucinationRate(target=0.05, window="24h"),
    ],
    error_budget=ErrorBudget(
        total=0.005,
        burn_rate_alert=2.0,      # Alert at 2x normal burn
        burn_rate_critical=10.0,  # Page at 10x burn
    )
)

# Record agent outcomes
slo.indicators[0].record_task(success=True)
slo.indicators[1].record_cost(cost_usd=0.35)
slo.indicators[2].record_evaluation(hallucinated=False)
slo.record_event(good=True)

# Check SLO health
status = slo.evaluate()  # HEALTHY, WARNING, CRITICAL, or EXHAUSTED
print(f"Budget remaining: {slo.error_budget.remaining_percent:.1f}%")
```

### 2. Deterministic Replay — Time-Travel Debugging for Agents

Capture every decision point in an agent's execution and replay it exactly:

```python
from agent_sre.replay.capture import TraceCapture, SpanKind, TraceStore

# Capture mode: records all decisions, tool calls, costs
with TraceCapture(agent_id="support-bot-v3", task_input="Refund order #12345") as capture:
    span = capture.start_span("tool_call", SpanKind.TOOL_CALL,
                              input_data={"tool": "lookup_order", "order_id": "12345"})
    # ... agent calls tool ...
    span.finish(output={"status": "found", "amount": 49.99}, cost_usd=0.02)

    span = capture.start_span("llm_inference", SpanKind.LLM_INFERENCE,
                              input_data={"prompt": "Process refund for $49.99"})
    span.finish(output={"decision": "approve_refund"}, cost_usd=0.15)

# Save trace for later replay
store = TraceStore()
store.save(capture.trace)
```

### 3. Progressive Delivery — Ship Agent Changes Safely

```yaml
# agent-sre.yaml — GitOps deployment spec
apiVersion: agent-sre/v1
kind: AgentRollout
metadata:
  name: support-bot-v4
spec:
  strategy:
    type: canary
    steps:
      - shadow: 100%     # Route all traffic to v4 in shadow mode, compare outputs
        duration: 1h
        analysis:
          - metric: task_success_rate
            threshold: 0.99
      - canary: 5%        # 5% real traffic to v4
        duration: 2h
        analysis:
          - metric: response_quality_score
            threshold: 0.95
          - metric: cost_per_task
            max_increase: 20%
      - canary: 25%
        duration: 4h
      - canary: 100%      # Full rollout
    rollback:
      automatic: true
      on:
        - error_budget_burn_rate > 5.0
        - policy_violations > 0
        - cost_anomaly_detected
```

### 4. Chaos Engineering — Break Agents on Purpose

```python
from agent_sre.chaos.engine import ChaosExperiment, Fault, AbortCondition

experiment = ChaosExperiment(
    name="tool-failure-resilience",
    target_agent="research-agent",
    faults=[
        Fault.tool_timeout("web_search", delay_ms=30_000),
        Fault.tool_error("database_query", error="connection_refused", rate=0.5),
        Fault.llm_latency("openai", p99_ms=15_000),
        Fault.delegation_reject("analyzer", rate=0.1),
    ],
    duration_seconds=1800,
    abort_conditions=[
        AbortCondition(metric="task_success_rate", threshold=0.80, comparator="lte"),
        AbortCondition(metric="cost_per_task", threshold=5.00, comparator="gte"),
    ],
)

experiment.start()
# Inject faults, observe agent behavior, measure resilience
for fault in experiment.faults:
    experiment.inject_fault(fault, applied=True)

resilience = experiment.calculate_resilience(
    baseline_success_rate=0.98,
    experiment_success_rate=0.88,
    recovery_time_ms=2500,
)
print(f"Resilience Score: {resilience.overall:.0f}/100")
```

### 5. Cost Guard — Prevent $10K Surprises

```python
from agent_sre.cost.guard import CostGuard

guard = CostGuard(
    per_task_limit=2.00,          # Hard cap per task
    per_agent_daily_limit=100.00, # Per agent per day
    org_monthly_budget=5000.00,   # Organization total
    anomaly_detection=True,       # Alert on unusual patterns
    auto_throttle=True,           # Slow down agents approaching limits
    kill_switch_threshold=0.95,   # Kill at 95% budget
)

# Before each task
allowed, reason = guard.check_task("my-agent", estimated_cost=0.50)
if not allowed:
    print(f"Blocked: {reason}")

# After each task
alerts = guard.record_cost("my-agent", "task-42", cost_usd=0.35)
for alert in alerts:
    print(f"⚠️ {alert.severity.value}: {alert.message}")
```

### 6. Incident Manager — When Agents Fail in Production

```python
from agent_sre.incidents.detector import IncidentDetector, Signal, SignalType

detector = IncidentDetector(correlation_window_seconds=300)

# Register automated responses
detector.register_response("slo_breach", ["auto_rollback", "notify_oncall"])
detector.register_response("cost_anomaly", ["throttle_agent", "generate_postmortem"])

# Ingest signals from your monitoring
signal = Signal(
    signal_type=SignalType.ERROR_BUDGET_EXHAUSTED,
    source="support-agent",
    message="Error budget consumed — freeze deployments",
)

incident = detector.ingest_signal(signal)
if incident:
    print(f"🚨 {incident.severity.value}: {incident.title}")
```

## The Full Stack

Agent SRE completes the governance-to-reliability stack:

| Layer | Project | What It Does |
|---|---|---|
| **Reliability** | **Agent SRE** (this) | SLOs, chaos testing, canary deploys, replay |
| **Networking** | [Agent Mesh](https://github.com/imran-siddique/agent-mesh) | Identity, trust, routing, delegation |
| **Kernel** | [Agent OS](https://github.com/imran-siddique/agent-os) | Policy enforcement, audit, compliance |

Together they form the **operating environment for production AI agents** — like Kubernetes + Istio + Prometheus, but purpose-built for non-deterministic agent workloads.

## Integration Points

### With Agent OS
- **Policy violations → SLO breaches**: Every Agent OS policy violation counts against the agent's error budget
- **Audit trail → Replay engine**: Agent OS audit logs provide the raw data for deterministic replay
- **Shadow mode hooks**: Agent OS shadow mode feeds into Agent SRE's progressive delivery pipeline

### With Agent Mesh
- **Trust scores → SLO indicators**: Agent Mesh trust scores become SLIs
- **Delegation chains → Distributed traces**: Every delegation hop becomes a trace span
- **Identity rotation → Deployment events**: Credential rotation is tracked as a reliability event
- **Registry → Deployment targets**: Agent Mesh registry provides the service catalog for canary rollouts

### With OpenTelemetry
- Native OTLP export for all SLIs and traces
- Custom semantic conventions for agent-specific telemetry
- Compatible with Grafana, Prometheus, Jaeger, and other OTLP-compatible backends

## Project Structure

```
agent-sre/
├── src/
│   └── agent_sre/
│       ├── slo/               # SLO definitions, SLI collectors, error budgets
│       ├── replay/            # Deterministic capture and replay engine
│       ├── delivery/          # Progressive delivery (shadow, canary, rollback)
│       ├── chaos/             # Chaos engineering and fault injection
│       ├── cost/              # Cost tracking, budgets, anomaly detection
│       ├── incidents/         # Detection, response, postmortem generation
│       ├── integrations/
│       │   ├── agent_os/      # Agent OS policy + audit integration
│       │   ├── agent_mesh/    # Agent Mesh identity + trust integration
│       │   └── otel/          # OpenTelemetry export
│       └── dashboard/         # Grafana dashboards and alerting rules
├── deployments/               # Kubernetes, Helm, docker-compose
├── examples/                  # End-to-end usage examples
├── tests/
├── docs/
└── specs/                     # SLO templates and chaos experiment specs
```

## Roadmap

See [Issues](https://github.com/imran-siddique/agent-sre/issues) for the full backlog, organized by priority.

## Why Not Just Use X?

**LangSmith / Arize / Langfuse** — Great for tracing and evaluation. But they don't give you SLOs, error budgets, canary deployments, chaos testing, or cost guardrails. Use them *together* with Agent-SRE: they tell you what happened, we tell you if it's within budget.

**Traditional APM (Prometheus, Grafana, Jaeger)** — Monitor infrastructure. Your dashboard says "HTTP 200, latency 150ms, all green" while your agent just approved a fraudulent transaction. Agent-SRE catches reasoning failures, not infrastructure failures.

**Cleric / Resolve / SRE.ai** — These use AI to help humans debug infrastructure. We apply SRE principles *to* AI agent systems. Completely different problem.

## Documentation

- [Getting Started](docs/getting-started.md) — Install and define your first SLO in 5 minutes
- [Concepts](docs/concepts.md) — Why agent reliability is different from infrastructure reliability
- [Integration Guide](docs/integration-guide.md) — Use with Agent-OS and AgentMesh
- [Comparison](docs/comparison.md) — Detailed comparison with other tools

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
