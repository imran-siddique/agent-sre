# Contributing to Agent SRE

Thank you for your interest in contributing to Agent SRE! This project brings site reliability engineering practices to AI agent systems. This guide will help you get set up and make your first contribution.

---

## Table of Contents

- [Getting Started](#-getting-started)
- [Development Setup](#-development-setup)
- [Code Style](#-code-style)
- [Making Changes](#-making-changes)
- [Testing](#-testing)
- [Issue Guidelines](#-issue-guidelines)
- [Architecture Overview](#-architecture-overview)
- [Getting Help](#-getting-help)

---

## 🚀 Getting Started

### Fork and Clone

```bash
# 1. Fork the repository on GitHub, then clone your fork
git clone https://github.com/<your-username>/agent-sre.git
cd agent-sre

# 2. Add upstream remote
git remote add upstream https://github.com/imran-siddique/agent-sre.git

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Run tests to verify your setup
python -m pytest

# 5. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 6. Verify the CLI works
agent-sre --help
```

### Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce code quality on every commit. The hooks include:

- **Trailing whitespace** and **end-of-file** fixes
- **YAML validation** and **merge conflict** detection
- **Private key detection** (security)
- **Ruff** linting and formatting
- **mypy** type checking (excludes tests)
- **pytest** check on push

Hooks are configured in `.pre-commit-config.yaml`. After installing with `pre-commit install`, they run automatically on `git commit`.

---

## 🛠️ Development Setup

### Python Version

Agent SRE requires **Python 3.10 or higher** and supports Python 3.10, 3.11, 3.12, and 3.13. We recommend using [pyenv](https://github.com/pyenv/pyenv) to manage Python versions:

```bash
pyenv install 3.12
pyenv local 3.12
```

### Virtual Environment

Always use a virtual environment for development:

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Install all dev dependencies
pip install -e ".[dev]"
```

### Optional Extras

Depending on what you're working on, install additional extras:

```bash
pip install -e ".[dev,api]"        # FastAPI server components
pip install -e ".[dev,otel]"       # OpenTelemetry OTLP exporter
pip install -e ".[dev,langchain]"  # LangChain integration
pip install -e ".[dev,datadog]"    # Datadog integration
pip install -e ".[dev,langfuse]"   # Langfuse observability
pip install -e ".[dev,all]"        # Everything
```

### IDE Recommendations

- **VS Code** with the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python), [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff), and [mypy](https://marketplace.visualstudio.com/items?itemName=ms-python.mypy-type-checker) extensions
- **PyCharm** Professional with built-in type checking enabled
- Enable format-on-save with Ruff for consistent formatting

---

## 📝 Code Style

### Formatting and Linting

We use **Ruff** for linting and formatting, and **mypy** for type checking:

```bash
# Format code
ruff format .

# Lint (with auto-fix)
ruff check . --fix

# Type check
mypy src/
```

### Rules

| Rule | Details |
|------|---------|
| **Line length** | 100 characters maximum |
| **Target version** | Python 3.10 |
| **Type hints** | Required on all function signatures |
| **Docstrings** | Required for all public modules, classes, and functions |
| **Docstring style** | Google style |
| **Import order** | Enforced by Ruff (`I` rule) — stdlib → third-party → local |
| **Lint rules** | `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`, `TCH` |

### Type Hints

All function signatures must include type hints. Use `from __future__ import annotations` for modern syntax:

```python
from __future__ import annotations

from agent_sre.slo.types import SLOResult

def evaluate_slo(
    agent_id: str,
    window_hours: int = 24,
    *,
    include_error_budget: bool = True,
) -> SLOResult:
    """Evaluate SLO compliance for an agent over a time window.

    Args:
        agent_id: The unique identifier of the agent to evaluate.
        window_hours: The lookback window in hours.
        include_error_budget: If True, include error budget calculations.

    Returns:
        The SLO evaluation result with compliance status and metrics.

    Raises:
        AgentNotFoundError: If the agent_id does not exist.
    """
    ...
```

### Docstrings (Google Style)

```python
class ChaosExperiment:
    """A fault injection experiment for testing agent resilience.

    Defines and executes controlled failure scenarios against agent
    systems to validate reliability and recovery behavior.

    Attributes:
        name: Human-readable experiment name.
        fault_type: The type of fault to inject (latency, error, kill).
        target: The agent or service to target.

    Example:
        >>> experiment = ChaosExperiment(
        ...     name="latency-spike",
        ...     fault_type="latency",
        ...     target="billing-agent",
        ... )
        >>> result = experiment.run(duration_seconds=60)
    """
```

---

## 🔀 Making Changes

### Branch Naming

Create a branch from `main` using one of these prefixes:

| Prefix | Use For |
|--------|---------|
| `feat/` | New features (e.g., `feat/canary-rollout-strategy`) |
| `fix/` | Bug fixes (e.g., `fix/slo-window-calculation`) |
| `docs/` | Documentation changes (e.g., `docs/chaos-engine-guide`) |
| `test/` | Test additions/improvements (e.g., `test/cost-guard-edge-cases`) |
| `refactor/` | Code refactoring (e.g., `refactor/incident-detector`) |

```bash
# Sync with upstream before branching
git fetch upstream
git checkout -b feat/my-feature upstream/main
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `perf`

**Scopes** (optional): `slo`, `replay`, `delivery`, `chaos`, `cost`, `incidents`, `cli`, `api`, `tracing`, `adapters`

**Examples:**

```
feat(slo): add latency percentile objectives
fix(chaos): prevent concurrent experiment conflicts
docs: add runbook authoring guide
test(cost): add budget overflow edge cases
perf(replay): optimize trace deserialization
```

### Pull Request Process

1. **Fork** the repository and create your branch
2. **Make changes** following the code style guidelines
3. **Write/update tests** — all new features need test coverage
4. **Run the full check suite:**
   ```bash
   ruff format .
   ruff check .
   mypy src/
   python -m pytest
   ```
5. **Push** your branch and open a Pull Request
6. **Fill out the PR description** with:
   - What changed and why
   - How to test the changes
   - Which engine/module is affected
   - Related issue numbers (e.g., `Closes #61`)
7. **Address review feedback** — maintainers may request changes
8. **Merge** — a maintainer will merge once approved

### Review Criteria

PRs are evaluated on:
- Correctness and edge case handling
- Test coverage for new/changed behavior
- Type safety (mypy must pass with `--strict`)
- Documentation for public APIs
- Engine independence (engines should work standalone)

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_slo_spec.py -v

# Run a specific test
python -m pytest tests/test_chaos_scheduler.py::test_schedule_experiment -v

# Run unit tests only
python -m pytest tests/unit/ -v

# Run integration tests only
python -m pytest tests/integration/ -v

# Run with coverage report
python -m pytest --cov=src/agent_sre --cov-report=html --cov-report=term-missing
```

### Writing Tests

- **Test file location:** Place tests in `tests/` at the repo root; use `tests/unit/` for unit tests and `tests/integration/` for integration tests
- **Naming convention:** `test_<module>.py` for files, `test_<behavior>` for functions
- **Async tests:** Use `pytest-asyncio` — tests are auto-detected (`asyncio_mode = "auto"`)
- **Adapter tests:** Each observability adapter (LangFuse, Datadog, Arize, etc.) has its own test file

```python
import pytest
from agent_sre.slo import SLODefinition, SLOEvaluator

class TestSLOEvaluator:
    """Tests for SLO evaluation logic."""

    def test_slo_passes_within_threshold(self) -> None:
        slo = SLODefinition(
            name="latency-p99",
            target=0.999,
            window_hours=24,
        )
        evaluator = SLOEvaluator(slo)
        result = evaluator.evaluate(current_value=0.9995)
        assert result.is_compliant is True

    def test_slo_fails_below_threshold(self) -> None:
        slo = SLODefinition(
            name="availability",
            target=0.999,
            window_hours=24,
        )
        evaluator = SLOEvaluator(slo)
        result = evaluator.evaluate(current_value=0.990)
        assert result.is_compliant is False

    @pytest.mark.asyncio
    async def test_async_slo_evaluation(self) -> None:
        slo = SLODefinition(name="throughput", target=100.0)
        result = await slo.evaluate_async(agent_id="test-agent")
        assert result.error_budget_remaining >= 0
```

### Coverage Requirements

- **Minimum coverage:** 80% for new code
- **Core engines** (SLO, chaos, incidents): aim for 90%+
- Run `python -m pytest --cov=src/agent_sre --cov-report=term-missing` to identify uncovered lines

### Test Organization

```
tests/
├── unit/                       # Fast, isolated unit tests
├── integration/                # Integration tests (may need services)
├── test_slo_spec.py            # SLO engine tests
├── test_chaos_scheduler.py     # Chaos engine tests
├── test_cost_optimizer.py      # Cost guard tests
├── test_alerts.py              # Alert system tests
├── test_experiments.py         # Experiment framework tests
├── test_fleet.py               # Fleet management tests
├── test_langchain_callback.py  # LangChain adapter tests
├── test_langfuse.py            # Langfuse adapter tests
├── test_datadog.py             # Datadog adapter tests
└── ...                         # 35+ test modules
```

---

## 📋 Issue Guidelines

### Bug Reports

When filing a bug, include:

1. **Agent SRE version** (`pip show agent-sre`)
2. **Python version** (`python --version`)
3. **Operating system**
4. **Steps to reproduce** — minimal code snippet or CLI commands
5. **Expected behavior** vs. **actual behavior**
6. **Full error traceback** if applicable
7. **Which engine** is affected (SLO, Chaos, Delivery, etc.)

### Feature Requests

For feature requests, describe:

1. **Use case** — what reliability problem does this solve?
2. **Proposed solution** — how should it work?
3. **Alternatives considered** — what else did you look at?
4. **Which engine** should this belong to (or is it a new module)?

### Good First Issues

New to the project? Look for issues labeled:

| Label | Description |
|-------|-------------|
| [`good first issue`](https://github.com/imran-siddique/agent-sre/labels/good%20first%20issue) | Small, well-defined tasks for newcomers |
| [`documentation`](https://github.com/imran-siddique/agent-sre/labels/documentation) | Improve docs, examples, and guides |
| [`help wanted`](https://github.com/imran-siddique/agent-sre/labels/help%20wanted) | Community contributions welcome |

---

## 🏗️ Architecture Overview

### Project Structure

```
agent-sre/
├── src/agent_sre/           # Main package
│   ├── slo/                 # SLO Engine — defines & measures agent reliability
│   ├── replay/              # Replay Engine — deterministic capture & replay
│   ├── delivery/            # Delivery Engine — progressive rollouts (canary, blue-green)
│   ├── chaos/               # Chaos Engine — fault injection testing
│   ├── cost/                # Cost Guard — budget management & anomaly detection
│   ├── incidents/           # Incident Manager — detection & response
│   ├── alerts/              # Alert routing and deduplication
│   ├── adapters/            # Observability platform adapters
│   ├── api/                 # FastAPI REST endpoints
│   ├── benchmarks/          # Performance benchmarking framework
│   ├── cascade/             # Cascade failure detection
│   ├── certification/       # Agent certification workflows
│   ├── cli/                 # Command-line interface
│   ├── evals/               # Evaluation framework
│   ├── experiments/         # Experiment tracking
│   ├── fleet/               # Fleet-wide agent management
│   ├── integrations/        # Third-party integrations
│   ├── k8s/                 # Kubernetes operator support
│   ├── mcp/                 # MCP server for tool exposure
│   ├── specs/               # Specification definitions
│   ├── tracing/             # Distributed tracing
│   └── providers.py         # Dependency injection providers
├── operator/                # Kubernetes operator
├── specs/                   # YAML spec definitions
├── examples/                # Working demos and usage examples
├── docs/                    # Documentation
├── tests/                   # Test suite (35+ test modules)
├── benchmarks/              # Benchmark configurations
├── charts/                  # Helm charts
├── dashboards/              # Grafana dashboards
└── deployments/             # Deployment configurations
```

### Core Engines

Each engine can be used independently or composed together for full-stack reliability:

| Engine | Module | Purpose | Key Abstractions |
|--------|--------|---------|------------------|
| **SLO Engine** | `slo/` | Define and measure agent reliability targets | `SLODefinition`, `SLOEvaluator`, `ErrorBudget` |
| **Replay Engine** | `replay/` | Deterministic capture and replay of agent traces | `TraceCapture`, `ReplaySession`, `GoldenTrace` |
| **Delivery Engine** | `delivery/` | Progressive rollouts with automated rollback | `Canary`, `BlueGreen`, `RolloutPolicy` |
| **Chaos Engine** | `chaos/` | Fault injection for resilience testing | `ChaosExperiment`, `FaultInjector`, `GameDay` |
| **Cost Guard** | `cost/` | Budget tracking and cost anomaly detection | `BudgetPolicy`, `CostTracker`, `AnomalyDetector` |
| **Incident Manager** | `incidents/` | Automated incident detection and response | `IncidentDetector`, `Runbook`, `EscalationPolicy` |

### Supporting Modules

| Module | Purpose |
|--------|---------|
| **adapters** | Connectors for Langfuse, Datadog, Arize, Helicone, W&B, MLflow, etc. |
| **alerts** | Alert routing, deduplication, and persistence |
| **cascade** | Cascade failure detection across agent dependencies |
| **certification** | Automated agent certification against SLO standards |
| **fleet** | Fleet-wide management and coordination |
| **tracing** | OpenTelemetry-based distributed tracing |

---

## 💬 Getting Help

- **Questions?** Open a [Discussion](https://github.com/imran-siddique/agent-sre/discussions)
- **Found a bug?** Open an [Issue](https://github.com/imran-siddique/agent-sre/issues)
- **Security issue?** See [SECURITY.md](SECURITY.md)

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
