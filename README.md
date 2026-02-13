# Agent SRE

**Reliability Engineering for AI Agent Systems**

> SRE practices adapted for multi-agent production environments. Not agents *doing* SRE — SRE *for* agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

# Define an SLO for your agent
slo = SLO(
    name="customer-support-agent",
    indicators=[
        SLI.task_success_rate(target=0.995, window="30d"),
        SLI.tool_accuracy(target=0.999, window="7d"),
        SLI.p95_latency(target_ms=5000, window="1h"),
        SLI.cost_per_task(target_usd=0.50, window="24h"),
    ],
    error_budget=ErrorBudget(
        burn_rate_alert=2.0,      # Alert at 2x normal burn
        burn_rate_critical=10.0,  # Page at 10x burn
        exhaustion_action="freeze_deployments",
    )
)
```

### 2. Deterministic Replay — Time-Travel Debugging for Agents

Capture every decision point in an agent's execution and replay it exactly:

```python
from agent_sre import ReplayEngine

# Capture mode: records all inputs, tool calls, LLM responses
with ReplayEngine.capture(agent_id="support-bot-v3") as recorder:
    result = agent.run("Refund order #12345")
    # Captures: prompt, tool calls, API responses, timestamps, costs

# Later: replay the exact execution
replay = ReplayEngine.load(trace_id="abc-123")
replay.step_through()  # Interactive step-by-step
replay.diff(other_trace_id="def-456")  # Compare two executions
replay.what_if(tool_responses={"lookup_order": modified_response})  # Counterfactual
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
from agent_sre.chaos import ChaosEngine, Fault

chaos = ChaosEngine(mesh_connection="agent-mesh://cluster-1")

# Inject faults into the agent mesh
experiment = chaos.create_experiment(
    name="tool-failure-resilience",
    target_agent="research-agent",
    faults=[
        Fault.tool_timeout("web_search", delay_ms=30000),
        Fault.tool_error("database_query", error="connection_refused", rate=0.5),
        Fault.llm_latency(provider="openai", p99_ms=15000),
        Fault.delegation_reject(from_agent="analyzer", rate=0.1),
    ],
    duration="30m",
    abort_conditions=[
        "task_success_rate < 0.80",   # Stop if quality drops too far
        "cost_per_task > 5.00",       # Stop if cost explodes
    ],
)
experiment.run()
```

### 5. Cost Guard — Prevent $10K Surprises

```python
from agent_sre import CostGuard

guard = CostGuard(
    per_task_limit=2.00,          # Hard cap per task
    per_agent_daily_limit=100.00, # Per agent per day
    org_monthly_budget=5000.00,   # Organization total
    anomaly_detection=True,       # Alert on unusual patterns
    auto_throttle=True,           # Slow down agents approaching limits
    kill_switch_threshold=0.95,   # Kill at 95% budget
)
```

### 6. Incident Manager — When Agents Fail in Production

```python
from agent_sre import IncidentManager

incidents = IncidentManager(
    detection=[
        "slo_breach",              # SLO violation detected
        "error_budget_exhausted",  # Error budget at 0
        "cost_anomaly",            # Unusual spending pattern
        "policy_violation",        # Agent OS policy breach
        "trust_revocation",        # Agent Mesh trust broken
    ],
    response=[
        "auto_rollback",           # Revert to last known good
        "circuit_breaker",         # Stop affected agent
        "generate_postmortem",     # Auto-generate incident report
        "replay_failing_traces",   # Capture traces for debugging
    ],
    notification=["slack", "pagerduty", "email"],
)
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
- Compatible with Grafana, Datadog, New Relic, Jaeger

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

## Positioning: Agent SRE vs. SRE Agents

| | Agent SRE (this project) | Azure SRE Agent / Others |
|---|---|---|
| **Purpose** | Make AI agents reliable | Use AI agents for infra ops |
| **Target** | Agent developers & platform teams | DevOps / SRE teams |
| **Monitors** | Agent reasoning, tool use, costs | Servers, VMs, K8s |
| **SLOs for** | Task success, accuracy, hallucination | Uptime, latency, error rate |
| **Chaos tests** | Tool failures, LLM latency, trust revocation | Network partition, pod kill |

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
