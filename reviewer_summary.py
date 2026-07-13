from __future__ import annotations

import json
from pathlib import Path

from experiment_manifest import ExperimentManifest


def write_summary(
    manifest: ExperimentManifest,
    result_path: Path,
    decision: str,
    output: Path,
) -> Path:
    result = json.loads(result_path.read_text())
    validation = result["metrics"]["validation"]
    relative = result["relative_metrics"]
    costs = result["cost_scenarios"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                f"# Research summary: {manifest.batch_id}",
                "",
                f"Decision: **{decision}**",
                "",
                f"Hypothesis: {manifest.hypothesis}",
                f"Universe: {manifest.intended_universe}",
                f"Mechanism: {manifest.economic_mechanism}",
                f"Causal inputs: {manifest.causal_inputs}",
                f"Expected failure regime: {manifest.expected_failure_regime}",
                f"Rejection condition: {manifest.rejection_condition}",
                "",
                "## Evidence",
                "",
                f"- Data SHA-256: `{result['data']['sha256']}`",
                f"- Strategy SHA-256: `{result['integrity']['strategy_sha256']}`",
                f"- Validation annual return: {validation['annual_return']:.2%}",
                f"- Validation Sharpe: {validation['sharpe']:.3f}",
                f"- Validation maximum drawdown: {validation['max_drawdown']:.2%}",
                f"- Excess annual return: {relative['excess_annual_return']:.2%}",
                f"- Cost scenarios: {json.dumps(costs, sort_keys=True)}",
                "",
            ]
        )
    )
    return output
