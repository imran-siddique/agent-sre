# Contributing to Agent SRE

Thank you for your interest in contributing to Agent SRE!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit using conventional commits: `feat:`, `fix:`, `docs:`, etc.
6. Push and open a PR

## Development Setup

```bash
git clone https://github.com/imran-siddique/agent-sre.git
cd agent-sre
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Architecture

Agent SRE is built as a modular framework with six core engines:

- **SLO Engine** (`src/agent_sre/slo/`) — Defines and measures agent reliability
- **Replay Engine** (`src/agent_sre/replay/`) — Deterministic capture and replay
- **Delivery Engine** (`src/agent_sre/delivery/`) — Progressive rollouts
- **Chaos Engine** (`src/agent_sre/chaos/`) — Fault injection testing
- **Cost Guard** (`src/agent_sre/cost/`) — Budget management and anomaly detection
- **Incident Manager** (`src/agent_sre/incidents/`) — Detection and response

Each engine can be used independently or together for full-stack reliability.

## Code Style

- Python 3.10+
- Type hints required
- Docstrings for all public APIs
- Tests for all new features

## Issues

Check the [issue tracker](https://github.com/imran-siddique/agent-sre/issues) for open items. Issues labeled `good first issue` are great starting points.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
