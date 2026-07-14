from __future__ import annotations

import json
from html import escape
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
    baseline = result["benchmark"]
    relative = result["relative_metrics"]
    costs = result["cost_scenarios"]
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        ("Hypothesis", manifest.hypothesis),
        ("Universe", manifest.intended_universe),
        ("Mechanism", manifest.economic_mechanism),
        ("Causal inputs", manifest.causal_inputs),
        ("Expected failure regime", manifest.expected_failure_regime),
        ("Rejection condition", manifest.rejection_condition),
    )
    details = "\n".join(
        f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>" for label, value in fields
    )
    evidence = (
        ("Data SHA-256", result["data"]["sha256"]),
        ("Strategy SHA-256", result["integrity"]["strategy_sha256"]),
        ("Validation annual return", f"{validation['annual_return']:.2%}"),
        ("Validation Sharpe", f"{validation['sharpe']:.3f}"),
        ("Validation maximum drawdown", f"{validation['max_drawdown']:.2%}"),
        ("Baseline annual return", f"{baseline['annual_return']:.2%}"),
        ("Baseline Sharpe", f"{baseline['sharpe']:.3f}"),
        ("Baseline maximum drawdown", f"{baseline['max_drawdown']:.2%}"),
        ("Excess annual return", f"{relative['excess_annual_return']:.2%}"),
        ("Cost scenarios", json.dumps(costs, sort_keys=True)),
    )
    evidence_html = "\n".join(
        f"<li><strong>{escape(label)}:</strong> {escape(str(value))}</li>"
        for label, value in evidence
    )
    output.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head><meta charset=\"utf-8\"><title>Research summary</title></head>",
                "<body>",
                f"<h1>Research summary: {escape(manifest.batch_id)}</h1>",
                f"<p><strong>Decision:</strong> {escape(decision)}</p>",
                f"<dl>{details}</dl>",
                "<h2>Evidence</h2>",
                f"<ul>{evidence_html}</ul>",
                "</body>",
                "</html>",
                "",
            ]
        )
    )
    return output
