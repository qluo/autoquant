from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from daily_controller import _remaining_attempts
from experiment_manifest import ExperimentManifest
from ledger import append_event
from reviewer_summary import write_summary


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

    def test_summary_includes_manifest_and_metrics(self) -> None:
        manifest = ExperimentManifest(
            "daily-1", "test", "trend", "equity ETFs", "underreaction",
            "adjusted close", "one", "ranges", "reject on no improvement",
        )
        result = {
            "data": {"sha256": "data"},
            "integrity": {"strategy_sha256": "strategy"},
            "metrics": {"validation": {"annual_return": 0.1, "sharpe": 1.0, "max_drawdown": -0.2}},
            "relative_metrics": {"excess_annual_return": 0.01},
            "cost_scenarios": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            output = root / "report.md"
            result_path.write_text(json.dumps(result))
            write_summary(manifest, result_path, "manual review", output)

            text = output.read_text()

        self.assertIn("Hypothesis: test", text)
        self.assertIn("Validation Sharpe: 1.000", text)
