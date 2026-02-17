"""Canary deployment evaluation script for GitHub Actions."""

import json
import os
import sys


def main():
    agent_name = os.environ.get("AGENT_NAME", "unknown")
    canary_pct = int(os.environ.get("CANARY_PCT", "10"))
    threshold = float(os.environ.get("PROMOTION_THRESHOLD", "0.95"))
    eval_window = int(os.environ.get("EVAL_WINDOW", "300"))

    print(f"\U0001f680 Canary deployment for '{agent_name}'")
    print(f"   Traffic: {canary_pct}%")
    print(f"   Promotion threshold: {threshold}")
    print(f"   Evaluation window: {eval_window}s")

    # Import agent-sre components
    try:
        from agent_sre.delivery import CanaryRollout, RolloutConfig
    except ImportError:
        print("\u26a0\ufe0f agent-sre delivery module not available, using basic evaluation")
        # Fallback: just set outputs
        _set_output("status", "evaluating")
        _set_output("slo_compliance", "1.0")
        return

    config = RolloutConfig(
        name=agent_name,
        canary_percent=canary_pct,
        promotion_threshold=threshold,
    )
    rollout = CanaryRollout(config)
    status = rollout.evaluate()

    _set_output("status", status)
    _set_output("slo_compliance", str(getattr(rollout, 'compliance', 1.0)))

    if status == "promoted":
        print("\u2705 Canary promoted \u2014 SLO compliance met")
    elif status == "rolled-back":
        print("\u274c Canary rolled back \u2014 SLO compliance below threshold")
        sys.exit(1)
    else:
        print("\u23f3 Canary still evaluating")


def _set_output(name: str, value: str) -> None:
    """Set GitHub Actions output."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"::set-output name={name}::{value}")


if __name__ == "__main__":
    main()
