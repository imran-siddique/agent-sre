# Changelog

All notable changes to Agent SRE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-02-19

### Added
- ARCHITECTURE.md documenting 7-engine architecture
- OpenTelemetry integration for distributed tracing
- SLO-as-Code YAML definitions with error budgets
- Incident runbook templates for common agent failures
- Golden signal traces for agent observability
- Chaos scheduling engine with 9 fault templates
- Blue-green deployment support for agent rollouts
- Cost optimization engine with budget guardrails
- Prometheus/Grafana dashboards for SLO monitoring
- GitHub Actions canary deployment action

### Changed
- Improved burn rate alert thresholds
- Enhanced error budget calculation precision

## [0.2.0] - 2026-02-01

### Added
- Core SLO Engine with 7 SLI types
- Replay Engine for deterministic capture/replay
- Progressive Delivery engine (shadow, canary, rollback)
- Chaos Engineering engine with fault injection
- Cost Guard engine with anomaly detection
- Incident Manager with auto-detection and postmortem
- Full test suite

## [0.1.0] - 2026-01-26

### Added
- Initial release
- Basic SLO definitions and evaluation
- Error budget tracking
- Agent OS and AgentMesh integration
