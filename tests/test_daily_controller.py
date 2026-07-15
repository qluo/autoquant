from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from daily_controller import (
    _remaining_attempts,
    _require_primary_checkout,
    _reviewed_strategy_source,
    _workspace_result_path,
)
from experiment_manifest import ExperimentManifest
from ledger import append_event
from reviewer_summary import write_summary
from sandbox_runner import _clear_stale_sandbox_result


class DailyControllerTests(unittest.TestCase):
    def test_manifest_requires_all_non_empty_fields(self) -> None:
        payload = {
            "batch_id": "daily-1",
            "hypothesis": "test hypothesis",
            "strategy_family": "trend",
            "intended_universe": "equity ETFs",
            "economic_mechanism": "underreaction",
            "causal_inputs": "adjusted close",
            "parameter_budget": "one fixed family",
            "expected_failure_regime": "range-bound market",
            "rejection_condition": "no Sharpe improvement",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(payload))
            manifest = ExperimentManifest.from_path(path)

        self.assertEqual(manifest.batch_id, "daily-1")
        self.assertEqual(manifest.universe_id, "qqq")

    def test_remaining_attempts_counts_batch_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite"
            append_event("attempt", {}, batch_id="daily-1", path=database)

            from unittest.mock import patch

            with patch("daily_controller.read_events") as read_events:
                read_events.return_value = [
                    {"event_type": "attempt", "batch_id": "daily-1"},
                    {"event_type": "attempt", "batch_id": "other"},
                ]
                self.assertEqual(_remaining_attempts("daily-1"), 19)

    def test_controller_rejects_linked_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").write_text("gitdir: /tmp/main/.git/worktrees/test\n")

            with self.assertRaisesRegex(RuntimeError, "primary repository checkout"):
                _require_primary_checkout(root)

    def test_reviewed_strategy_source_must_be_primary_strategy_file(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "strategy.py"
            source.write_text("def generate_signals(bars): return []\n")
            with patch("daily_controller.ROOT", root):
                self.assertEqual(_reviewed_strategy_source(source), source)
                with self.assertRaisesRegex(ValueError, "primary checkout"):
                    _reviewed_strategy_source(root / "other.py")

    def test_sandbox_replaces_stale_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            output = output_dir / "latest_result.json"
            output.write_text("stale")

            self.assertEqual(_clear_stale_sandbox_result(output_dir), output)
            self.assertFalse(output.exists())

    def test_controller_uses_sandbox_result_when_canonical_result_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            sandbox_result = workspace / "runs/sandbox/latest_result.json"
            sandbox_result.parent.mkdir(parents=True)
            sandbox_result.write_text("result")

            self.assertEqual(_workspace_result_path(workspace), sandbox_result)

    def test_controller_reports_missing_workspace_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "sandbox completed"):
                _workspace_result_path(Path(directory))

    def test_summary_includes_manifest_and_metrics(self) -> None:
        manifest = ExperimentManifest(
            "daily-1", "test", "trend", "equity ETFs", "underreaction",
            "adjusted close", "one", "ranges", "reject on no improvement",
        )
        result = {
            "data": {"sha256": "data"},
            "integrity": {"strategy_sha256": "strategy"},
            "metrics": {"validation": {"annual_return": 0.1, "sharpe": 1.0, "max_drawdown": -0.2}},
            "benchmark": {"annual_return": 0.08, "sharpe": 0.8, "max_drawdown": -0.25},
            "relative_metrics": {"excess_annual_return": 0.01},
            "cost_scenarios": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            output = root / "report.html"
            result_path.write_text(json.dumps(result))
            write_summary(manifest, result_path, "manual review", output)

            text = output.read_text()

        self.assertIn("<dt>Hypothesis</dt><dd>test</dd>", text)
        self.assertIn("<th>Metric</th><th>Current run</th><th>Baseline</th>", text)
        self.assertIn("<th scope=\"row\">Sharpe</th><td>1.000</td><td>0.800</td>", text)
