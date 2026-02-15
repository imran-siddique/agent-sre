<div align="center">

# Agent SRE

**Reliability Engineering for AI Agent Systems**

*SLOs · Error Budgets · Chaos Testing · Progressive Delivery · Cost Guardrails*

[![GitHub Stars](https://img.shields.io/github/stars/imran-siddique/agent-sre?style=social)](https://github.com/imran-siddique/agent-sre/stargazers)
[![Sponsor](https://img.shields.io/badge/sponsor-❤️-ff69b4)](https://github.com/sponsors/imran-siddique)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![CI](https://github.com/imran-siddique/agent-sre/actions/workflows/ci.yml/badge.svg)](https://github.com/imran-siddique/agent-sre/actions/workflows/ci.yml)
[![Agent-OS Compatible](https://img.shields.io/badge/agent--os-compatible-green.svg)](https://github.com/imran-siddique/agent-os)
[![AgentMesh Compatible](https://img.shields.io/badge/agentmesh-compatible-green.svg)](https://github.com/imran-siddique/agent-mesh)

> ⭐ **If this project helps you, please star it!** It helps others discover Agent SRE.

> 🔗 **Part of the Agent Ecosystem** — Works with [Agent OS](https://github.com/imran-siddique/agent-os) (governance) and [AgentMesh](https://github.com/imran-siddique/agent-mesh) (identity & trust)

[Quick Start](#-quick-start-in-30-seconds) • [Examples](examples/) • [Docs](docs/) • [Agent OS](https://github.com/imran-siddique/agent-os) • [AgentMesh](https://github.com/imran-siddique/agent-mesh)

</div>

---

## ⚡ Quick Start in 30 Seconds

```bash
pip install agent-sre
```

```python
from agent_sre import SLO, ErrorBudget
from agent_sre.slo.indicators import TaskSuccessRate, CostPerTask, HallucinationRate

# Define what "reliable" means for your agent
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
print(f"Budget remaining: {slo.error_budget.remaining_percent:.1f}%")
```

That's it. Your agent now has SLOs, error budgets, and burn rate alerts. [See all examples →](examples/)

---

## The Problem

AI agents in production fail differently than traditional services:

| Failure Mode | Traditional Service | AI Agent |
|---|---|---|
| **Crash** | Stack trace, restart | Same — but rare |
| **Wrong answer** | N/A | Returns "success" but the answer is wrong |
| **Silent degradation** | Latency spike | Reasoning quality drops, no metric moves |
| **Cost explosion** | Predictable | Runaway tool loops burn $10K in minutes |
| **Cascade failure** | Service A → B | Agent A trusts Agent B who hallucinates |
| **Tool drift** | API versioning | MCP server schema changes silently break workflows |

Your APM dashboard says "HTTP 200, latency 150ms, all green" while your agent just approved a fraudulent transaction.

**Traditional monitoring catches crashes. Agent SRE catches *everything else*.**

## The Solution

Agent SRE brings Site Reliability Engineering to AI agents — the same discipline that keeps Google, Netflix, and Spotify reliable, adapted for non-deterministic agent workloads.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Your AI Agents                             │
├─────────────────────────────────────────────────────────────────┤
│  Agent SRE — The Reliability Lifecycle                          │
│                                                                 │
│  1. DEFINE    SLOs — what does "reliable" mean?                  │
│  2. MEASURE   SLIs — are we meeting those targets?              │
│  3. PROTECT   Cost Guard + Circuit Breaker — prevent disasters  │
│  4. SHIP      Shadow + Canary — deploy changes safely           │
│  5. BREAK     Chaos Engine — prove resilience before prod does  │
│  6. RESPOND   Incidents + Postmortem — recover fast             │
│  7. LEARN     Replay + Diff — understand exactly what happened  │
├─────────────────────────────────────────────────────────────────┤
│  AgentMesh — Identity, Trust, Routing                           │
├─────────────────────────────────────────────────────────────────┤
│  Agent OS — Policy Enforcement, Audit, Compliance               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Capabilities

### 1. SLO Engine — Define What "Reliable" Means

Traditional SRE defines SLOs for services (99.9% uptime). Agent SRE defines SLOs for *agent behavior*:

| SLI (Indicator) | Example SLO | What It Catches |
|---|---|---|
| **Task Success Rate** | 99.5% of tasks correct | Silent reasoning failures |
| **Tool Call Accuracy** | 99.9% correct tool selection | Wrong tool, wrong arguments |
| **Response Latency (P95)** | < 5s single-step | Stuck in reasoning loops |
| **Cost Per Task** | < $0.50 mean | Runaway tool loops |
| **Policy Compliance** | 100% adherence | Safety violations |
| **Delegation Chain Depth** | ≤ 3 hops | Unbounded delegation |
| **Hallucination Rate** | < 1% factual errors | Confident wrong answers |

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

slo.record_event(good=True)
status = slo.evaluate()  # HEALTHY | WARNING | CRITICAL | EXHAUSTED
```

### 2. Replay Engine — Time-Travel Debugging for Agents

Capture every decision point and replay it exactly:

```python
from agent_sre.replay.capture import TraceCapture, SpanKind, TraceStore

# Capture mode: records all decisions, tool calls, costs
with TraceCapture(agent_id="support-bot-v3", task_input="Refund order #12345") as capture:
    span = capture.start_span("tool_call", SpanKind.TOOL_CALL,
                              input_data={"tool": "lookup_order", "order_id": "12345"})
    span.finish(output={"status": "found", "amount": 49.99}, cost_usd=0.02)

    span = capture.start_span("llm_inference", SpanKind.LLM_INFERENCE,
                              input_data={"prompt": "Process refund for $49.99"})
    span.finish(output={"decision": "approve_refund"}, cost_usd=0.15)

# Save trace, replay later, diff with production
store = TraceStore()
store.save(capture.trace)
```

Features: deterministic replay, trace diffing, counterfactual "what-if" analysis, multi-agent distributed traces, automatic PII redaction.

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
      - shadow: 100%     # Route all traffic to v4 in shadow mode
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
for fault in experiment.faults:
    experiment.inject_fault(fault, applied=True)

resilience = experiment.calculate_resilience(
    baseline_success_rate=0.98,
    experiment_success_rate=0.88,
    recovery_time_ms=2500,
)
print(f"Resilience Score: {resilience.overall:.0f}/100")
```

9 pre-built experiment templates: tool timeout, error storms, LLM degradation, cascading failures, cost explosions, and more.

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

Anomaly detection uses Z-score, IQR, and EWMA methods with severity scoring.

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

Features: signal correlation, deduplication, circuit breaker per agent, automated postmortem generation with timeline and action items.

---

## Ecosystem Integration

Agent SRE completes the governance-to-reliability stack:

| Layer | Project | What It Does |
|---|---|---|
| **Reliability** | **Agent SRE** (this) | SLOs, chaos testing, canary deploys, cost guard, replay |
| **Networking** | [AgentMesh](https://github.com/imran-siddique/agent-mesh) | Identity, trust, routing, delegation |
| **Kernel** | [Agent OS](https://github.com/imran-siddique/agent-os) | Policy enforcement, audit, compliance |

### With Agent OS
- Policy violations → SLO breaches (every violation counts against error budget)
- Audit trail → Replay engine (raw data for deterministic replay)
- Shadow mode → Progressive delivery pipeline

### With AgentMesh
- Trust scores → SLI indicators (mesh trust becomes an SLI)
- Delegation chains → Distributed traces (every hop is a span)
- Identity rotation → Deployment events (tracked as reliability events)

### With OpenTelemetry
- Native OTLP export for all SLIs and traces
- Custom semantic conventions for agent-specific telemetry
- Compatible with Grafana, Prometheus, Jaeger, and other OTLP-compatible backends

---

## Architecture

```
agent-sre/
├── src/agent_sre/
│   ├── slo/               # SLO definitions, SLI collectors, error budgets
│   │   ├── indicators.py  # 7 built-in SLIs (task success, cost, hallucination, etc.)
│   │   ├── objectives.py  # SLO engine with burn rate alerts
│   │   └── dashboard.py   # SLO dashboard with compliance history
│   ├── replay/            # Deterministic capture and replay engine
│   │   ├── capture.py     # Trace capture with PII redaction
│   │   ├── engine.py      # Replay, diff, counterfactual analysis
│   │   ├── visualization.py  # Execution graphs, critical path
│   │   └── distributed.py # Multi-agent trace reconstruction
│   ├── delivery/          # Progressive delivery (shadow, canary, rollback)
│   │   ├── rollout.py     # Shadow mode, canary rollouts, traffic splitting
│   │   └── gitops.py      # Declarative rollout specs (YAML)
│   ├── chaos/             # Chaos engineering and fault injection
│   │   ├── engine.py      # Experiment state machine, resilience scoring
│   │   └── library.py     # 9 pre-built experiment templates
│   ├── cost/              # Cost tracking, budgets, anomaly detection
│   │   ├── guard.py       # Hierarchical budgets, auto-throttle, kill switch
│   │   └── anomaly.py     # Z-score, IQR, EWMA anomaly detection
│   ├── incidents/         # Detection, response, postmortem generation
│   │   ├── detector.py    # Signal correlation, deduplication, routing
│   │   ├── circuit_breaker.py  # Per-agent circuit breaker (CLOSED/OPEN/HALF_OPEN)
│   │   └── postmortem.py  # Automated postmortem with timeline + action items
│   └── integrations/      # Ecosystem bridges
│       ├── agent_os/      # Agent OS policy + audit → SLI bridge
│       ├── agent_mesh/    # AgentMesh trust score → SLI bridge
│       └── otel/          # OpenTelemetry export
├── examples/              # 4 runnable demos
├── tests/                 # 44+ test functions
├── docs/                  # Getting started, concepts, integration guide
└── specs/                 # SLO templates (coming soon)
```

---

## How It Differs

**Observability tools** (LangSmith, Langfuse, Arize) tell you *what happened*.
Agent SRE tells you *if it was within budget* and *what to do about it*.

| | Observability Tools | Agent SRE |
|---|---|---|
| Tracing | ✅ Core strength | ✅ Trace capture + deterministic replay |
| Evaluation | ✅ LLM-as-judge | ✅ SLI recording |
| **SLOs & Error Budgets** | ❌ | ✅ Define reliability targets |
| **Canary Deployments** | ❌ | ✅ Compare agent versions safely |
| **Chaos Testing** | ❌ | ✅ Inject faults, measure resilience |
| **Cost Guardrails** | ❌ (cost tracking only) | ✅ Per-task limits, auto-throttle, kill switch |
| **Incident Detection** | ❌ | ✅ SLO breach → auto-incident → postmortem |
| **Progressive Rollout** | ❌ | ✅ Shadow mode, traffic splitting, rollback |

**Use both together:** observability for deep trace debugging, Agent SRE for production reliability operations.

**AI-powered SRE tools** (Cleric, Resolve, SRE.ai) use AI to help humans debug *infrastructure*. Agent SRE applies SRE principles *to AI agent systems*. Completely different target.

**Traditional APM** (Prometheus, Grafana, Jaeger) monitors infrastructure. Your dashboard says "HTTP 200, latency 150ms, all green" while your agent just approved a fraudulent transaction. Agent SRE catches reasoning failures, not infrastructure failures.

---

## Status & Maturity

### ✅ Fully Implemented (6,000+ lines, 44+ tests)

| Component | Status | Description |
|---|---|---|
| **SLO Engine** | ✅ Stable | 7 SLI types, error budgets, burn rate alerts, time windows |
| **Replay Engine** | ✅ Stable | Capture, replay, diff, counterfactual, distributed traces |
| **Progressive Delivery** | ✅ Stable | Shadow mode, canary rollouts, analysis gates, auto-rollback |
| **Chaos Engine** | ✅ Stable | 9 fault templates, resilience scoring, abort conditions |
| **Cost Guard** | ✅ Stable | Hierarchical budgets, anomaly detection, auto-throttle |
| **Incident Manager** | ✅ Stable | Signal correlation, circuit breaker, automated postmortem |
| **Agent OS Bridge** | ✅ Stable | Policy violations → SLI, audit entries → signals |
| **AgentMesh Bridge** | ✅ Stable | Trust scores → SLI, mesh events → signals |

### ⚠️ In Progress

| Component | Status | Notes |
|---|---|---|
| OpenTelemetry export | 🔶 Stub | Dependencies wired, exporter not yet implemented |
| Deployment configs | 🔶 Empty | `deployments/` folder exists, no Docker/Helm yet |
| SLO templates | 🔶 Empty | `specs/` folder exists, no pre-built configs yet |
| Integration tests | 🔶 Empty | `integration/` folder exists, unit tests only |

---

## Examples

| Example | Description | Command |
|---|---|---|
| [Quickstart](examples/quickstart.py) | SLO + cost + incident in one script | `python examples/quickstart.py` |
| [Cost Guard](examples/cost_guard.py) | Budget enforcement with throttling | `python examples/cost_guard.py` |
| [Canary Rollout](examples/canary_rollout.py) | Shadow + canary with auto-rollback | `python examples/canary_rollout.py` |
| [Chaos Test](examples/chaos_test.py) | Fault injection and resilience scoring | `python examples/chaos_test.py` |

---

## Documentation

- [Getting Started](docs/getting-started.md) — Install and define your first SLO in 5 minutes
- [Concepts](docs/concepts.md) — Why agent reliability is different from infrastructure reliability
- [Integration Guide](docs/integration-guide.md) — Use with Agent OS, AgentMesh, and OpenTelemetry
- [Comparison](docs/comparison.md) — Detailed comparison with other tools

---

## Contributing

```bash
git clone https://github.com/imran-siddique/agent-sre.git
cd agent-sre
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — See [LICENSE](LICENSE) for details.

---

<div align="center">

**Observability tells you what happened. Agent SRE tells you if it was within budget.**

[GitHub](https://github.com/imran-siddique/agent-sre) · [Docs](docs/) · [Agent OS](https://github.com/imran-siddique/agent-os) · [AgentMesh](https://github.com/imran-siddique/agent-mesh)

</div>
