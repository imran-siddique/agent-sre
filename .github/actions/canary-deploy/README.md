# Agent SRE Canary Deploy Action

Progressive canary deployment for AI agents with SLO-based auto-promotion.

## Usage

```yaml
- name: Canary Deploy
  uses: ./.github/actions/canary-deploy
  with:
    agent-name: my-agent
    canary-percentage: '10'
    promotion-threshold: '0.95'
    evaluation-window: '300'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `agent-name` | Yes | — | Name of the agent to deploy |
| `canary-percentage` | No | `10` | Initial canary traffic percentage (0-100) |
| `promotion-threshold` | No | `0.95` | SLO compliance threshold for auto-promotion (0.0-1.0) |
| `evaluation-window` | No | `300` | Time in seconds to evaluate canary before promotion |
| `python-version` | No | `3.12` | Python version to use |

## Outputs

| Output | Description |
|--------|-------------|
| `status` | Deployment status: `promoted`, `rolled-back`, or `evaluating` |
| `slo-compliance` | SLO compliance score at end of evaluation |
